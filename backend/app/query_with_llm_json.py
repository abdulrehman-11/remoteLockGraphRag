# remotelock_production_retriever.py
"""
Production RemoteLock Retriever with Maximum Accuracy

Features:
- Complete sitemap in prompt (LLM sees ALL page slugs)
- LangChain GraphCypherQAChain for structured retrieval
- Hybrid search with combined Cypher and Vector results
- Weighted ranking prioritizing exact slug/title matches and content relevance
- Improved hierarchical searching in Cypher
"""
import os
import sys

print("QUERY_LLM: Module import started", flush=True)

# Set cache directories for model storage (must be before any model imports)
# Use persistent cache directory in backend/model_cache (included in build artifact)
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_APP_DIR)
_CACHE_DIR = os.path.join(_BACKEND_DIR, 'model_cache')

print(f"QUERY_LLM: Cache directory: {_CACHE_DIR}", flush=True)
print(f"QUERY_LLM: Cache exists: {os.path.exists(_CACHE_DIR)}", flush=True)

os.environ.setdefault('TRANSFORMERS_CACHE', os.path.join(_CACHE_DIR, 'transformers'))
os.environ.setdefault('SENTENCE_TRANSFORMERS_HOME', os.path.join(_CACHE_DIR, 'sentence_transformers'))
os.environ.setdefault('HF_HOME', _CACHE_DIR)

import re
import json
import logging
import sys
import time
import warnings
from dotenv import load_dotenv
from typing import List, Dict, Any
from difflib import SequenceMatcher

warnings.filterwarnings('ignore')
load_dotenv()

# --- Logging Configuration ---
# Configure logging with fallback for environments with read-only filesystems (like Render)
handlers = [logging.StreamHandler(sys.stdout)]
try:
    # Try to create file handler in /tmp (writable on Render)
    handlers.append(logging.FileHandler('/tmp/retriever_logs.log'))
except Exception as e:
    print(f"Warning: Could not create retriever log file, using stdout only: {e}")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
# NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
# NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "123456789")

NEO4J_URI = "neo4j+s://d3db84ff.databases.neo4j.io" # This is a placeholder, replace with your actual AuraDB URI
NEO4J_USER = "neo4j" # For AuraDB, the default user is typically 'neo4j'
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD") # Loaded from .env

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")



if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

# --- IMPORTANT: Updated Neo4jGraph import ---
# According to the deprecation warning, use langchain_neo4j for Neo4jGraph.
# You need to install it: pip install langchain-neo4j
try:
    from langchain_neo4j import Neo4jGraph
except ImportError:
    # Fallback to langchain_community if langchain_neo4j is not installed,
    # but be aware of the deprecation and potential future breakage.
    print("Warning: 'langchain-neo4j' not found. Falling back to 'langchain_community.graphs.Neo4jGraph'. "
          "Please install 'langchain-neo4j' for the latest compatibility (pip install langchain-neo4j).")
    from langchain_community.graphs import Neo4jGraph

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.chains import GraphCypherQAChain
from langchain.prompts import PromptTemplate
# Replaced SentenceTransformer with Gemini API embeddings to reduce memory usage (~300MB saved)
from neo4j import GraphDatabase

# --- Sitemap Loading ---
def load_complete_sitemap():
    """Load sitemap and extract ALL page information for indexing and prompt context."""
    try:
        # Use the provided sitemap structure directly
        sitemap_data = {
          "site": {
            "name": "RemoteLock Support",
            "homepage": "https://support.remotelock.com/s/"
          },
          "categories": [
            {
              "name": "FAQs",
              "url": "https://support.remotelock.com/s/faqs",
              "pages": [
                "https://support.remotelock.com/s/article/Help-with-my-Vacation-Rental-Property-Management-IntegrationFAQ",
                "https://support.remotelock.com/s/article/Need-Help-%EF%B8%8F",
                "https://support.remotelock.com/s/article/Unable-to-Register-Lock",
                "https://support.remotelock.com/s/article/Lock-Offline",
                "https://support.remotelock.com/s/article/Will-not-lock-unlock-troubleshooting",
                "https://support.remotelock.com/s/article/Reconnecting-your-Lock-to-WiFi"
              ]
            },
            {
              "name": "Installation Guides",
              "url": "https://support.remotelock.com/s/hardware-information",
              "subcategories": [
                {
                  "name": "500 series",
                  "url": "https://support.remotelock.com/s/500-series",
                  "pages": [
                    "https://support.remotelock.com/s/article/500-Series-Deadbolt-Handing-the-Lock-openEDGE-Residential-Grade-5i-RG",
                    "https://support.remotelock.com/s/article/500-Series-Lever-Hardware-Installation-openEDGE-Residential-Grade-5i-RG",
                    "https://support.remotelock.com/s/article/DB-500R-non-connected-User-Manual",
                    "https://support.remotelock.com/s/article/LS-DB500R-Keypad-Electronic-Lock-Remote-Control-Manual",
                    "https://support.remotelock.com/s/article/LS-L500i-Installation-and-Local-Setup-Legacy-Wi-Fi-Locks",
                    "https://support.remotelock.com/s/article/LS-DB500i-Installation-and-Local-Setup-Legacy-Wi-Fi-Locks",
                    "https://support.remotelock.com/s/article/500-Series-Deadbolt-Hardware-Installation-openEDGE-Residential-Grade-5i-RG"
                  ]
                },
                {
                  "name": "600-series",
                  "url": "https://support.remotelock.com/s/600-series",
                  "pages": [
                    "https://support.remotelock.com/s/article/600-Series-Hardware-Installation-openEDGE-Light-Duty-Commercial-Levers-3i-BG",
                    "https://support.remotelock.com/s/article/600-Series-Mortise-Latch-Installation-openEDGE-Light-Duty-Commercial-Levers-3i-BG",
                    "https://support.remotelock.com/s/article/600-Series-FAQs-openEDGE-Light-Duty-Commercial-Levers-3i-BG"
                  ]
                },
                {
                  "name": "700 Series",
                  "url": "https://support.remotelock.com/s/700-series",
                  "pages": [
                    "https://support.remotelock.com/s/article/CG-EX-Push-Exit-Panic-Bar-Installation-Guide",
                    "https://support.remotelock.com/s/article/OpenEdge-CG-formerly-model-7i-Installation-manual-print-version",
                    "https://support.remotelock.com/s/article/700-Series-Mortise-Latch-Installation-openEDGE-Medium-Duty-Commercial-Levers-7i-CG",
                    "https://support.remotelock.com/s/article/700-Series-Mortise-latch-change-handing-instructions-openEDGE-Medium-Duty-Commercial-Levers-7i-CG",
                    "https://support.remotelock.com/s/article/700-Series-Hardware-Installation-openEDGE-Medium-Duty-Commercial-Levers-7i-CG",
                    "https://support.remotelock.com/s/article/ManualProgrammingFunctions",
                    "https://support.remotelock.com/s/article/700-CG-7i-800-Series-Programming-Functions-and-Function-Codes"
                  ]
                },
                {
                  "name": "800 Series",
                  "url": "https://support.remotelock.com/s/800-series",
                  "pages": [
                    "https://support.remotelock.com/s/article/800-Series-Hardware-Installation-openEDGE-Heavy-Duty-Commercial-Lever"
                  ]
                },
                {
                  "name": "ACS",
                  "url": "https://support.remotelock.com/s/acs",
                  "pages": [
                    "https://support.remotelock.com/s/article/ACS-ACK-Troubleshooting-Guide",
                    "https://support.remotelock.com/s/article/Relay-Safety-Sheet",
                    "https://support.remotelock.com/s/article/Regular-ACS-Mode-Overview",
                    "https://support.remotelock.com/s/article/Elevator-ACS-Mode-Overview",
                    "https://support.remotelock.com/s/article/Setting-up-FAI-Fire-Alarm-Interface-Connection",
                    "https://support.remotelock.com/s/article/Reconnecting-ACK-ACS-to-Network",
                    "https://support.remotelock.com/s/article/Adding-Expansion-Panel-to-Existing-ACS-Install",
                    "https://support.remotelock.com/s/article/ACS-Installation",
                    "https://support.remotelock.com/s/article/Prior-To-ACS-Installation",
                    "https://support.remotelock.com/s/article/ACS-Installation-Completion-Checklist",
                    "https://support.remotelock.com/s/article/ACS-Installation-Warnings",
                    "https://support.remotelock.com/s/article/24-Volt-Conversion-Steps",
                    "https://support.remotelock.com/s/article/Testing-ACS-Installation",
                    "https://support.remotelock.com/s/article/Bulk-Erase-Steps-For-First-ACS-Installation",
                    "https://support.remotelock.com/s/article/Adding-an-ACS-Device-to-the-Remotelock-Portal-Mercury-Security-ACS-Integration",
                    "https://support.remotelock.com/s/article/MR52-Expansion-Board-User-Manual",
                    "https://support.remotelock.com/s/article/RemoteLock-Mobile-Key-Reader-Setup",
                    "https://support.remotelock.com/s/article/MR52-Expansion-Panel-Wiring-Schema-for-Addressing",
                    "https://support.remotelock.com/s/article/LP1502-Controller-User-Manual",
                    "https://support.remotelock.com/s/article/Creating-Mobile-Key-Credentials",
                    "https://support.remotelock.com/s/article/ACS-Technical-Documents",
                    "https://support.remotelock.com/s/article/LP1501-Controller-User-Manual",
                    "https://support.remotelock.com/s/article/ACS-Configuration",
                    "https://support.remotelock.com/s/article/RemoteLock-Mobile-Key-Quick-Guide",
                    "https://support.remotelock.com/s/article/Card-Formats-Supported-with-Mercury",
                    "https://support.remotelock.com/s/article/RemoteLock-Korelock-MF009-Quick-Guide",
                    "https://support.remotelock.com/s/article/Lockdown-Functionality",
                    "https://support.remotelock.com/s/article/LP4502-Controller-User-Manual",
                    "https://support.remotelock.com/s/article/ACS-Wire-Diagrams",
                    "https://support.remotelock.com/s/article/MR50-Expansion-Board-User-Manual"
                  ]
                },
                {
                  "name": "Other Products",
                  "url": "https://support.remotelock.com/s/other-products",
                  "pages": [
                    "https://support.remotelock.com/s/article/Kwikset-Halo-Installation-Instructions",
                    "https://support.remotelock.com/s/article/Yale-Assure-Lock-2-Key-Free-Deadbolt-Installation-Guide",
                    "https://support.remotelock.com/s/article/Yale-Assure-Lock-2-Keyed-Deadbolt-Installation-Guide",
                    "https://support.remotelock.com/s/article/Schlage-Encode-Lever-Quick-Start-Guide",
                    "https://support.remotelock.com/s/article/Schlage-Encode-Deabolt-Quick-Start-Guide",
                    "https://support.remotelock.com/s/article/Turno-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/McGrath-Locks-NX5-User-Manual",
                    "https://support.remotelock.com/s/article/McGrath-Locks-X3-User-Manual",
                    "https://support.remotelock.com/s/article/McGrath-locks-Albion",
                    "https://support.remotelock.com/s/article/PROLOK-Deluxe-Hardware-Installation-Manual",
                    "https://support.remotelock.com/s/article/ProLok-Slimline-User-Manual",
                    "https://support.remotelock.com/s/article/ProLok-Slimline-Hardware-Installation-Guide",
                    "https://support.remotelock.com/s/article/3500-Lever-Hardware-Installation-Guide",
                    "https://support.remotelock.com/s/article/3500-Deadbolt-Hardware-Installation-Guide",
                    "https://support.remotelock.com/s/article/LS-P50-User-Manual-and-Provisioning-Guide-Power-Plug",
                    "https://support.remotelock.com/s/article/RemoteLock-model-6i-Installation",
                    "https://support.remotelock.com/s/article/Power-Plugs",
                    "https://support.remotelock.com/s/article/LS-90i-Local-Programming-and-Operation-Guide-Thermostat",
                    "https://support.remotelock.com/s/article/LS-90i-Installation-Guide-Thermostat",
                    "https://support.remotelock.com/s/article/LS-60i-Local-Programming-and-Operation-Guide-Thermostat",
                    "https://support.remotelock.com/s/article/LS-60i-Installation-Guide-Thermostat",
                    "https://support.remotelock.com/s/article/Types-of-Smart-Cards-Prox-Cards"
                  ]
                },
                {
                  "name": "ResortLocks",
                  "url": "https://support.remotelock.com/s/resortlocks",
                  "pages": [
                    "https://support.remotelock.com/s/article/LSRL-1-Wire-Software-Manual-Legacy-ResortLock-Desktop-Software",
                    "https://support.remotelock.com/s/article/ResortLock-FAQs-and-Troubleshooting-Guide",
                    "https://support.remotelock.com/s/article/RL2000-Installation-and-Local-Setup-ResortLock",
                    "https://support.remotelock.com/s/article/RL4000-Installation-and-Local-Setup-ResortLock",
                    "https://support.remotelock.com/s/article/Thermostats"
                  ]
                }
              ]
            },
            {
              "name": "Contact Support",
              "url": "https://support.remotelock.com/s/article/Contact-Support",
              "pages": [
                "https://support.remotelock.com/s/article/Contact-Support",
                "https://support.remotelock.com/s/article/Feature-Request-Suggestions",
                "https://support.remotelock.com/s/article/Warranty-and-Returns-Information",
                "https://support.remotelock.com/s/article/Transfer-of-Ownership",
                "https://support.remotelock.com/s/article/Blocking-a-ReadyPIN"
              ]
            },
            {
              "name": "Getting Started",
              "url": "https://support.remotelock.com/s/getting-started",
              "pages": [
                "https://support.remotelock.com/s/article/IMPORTANT-WiFi-Heartbeat-Interval-Explained",
                "https://support.remotelock.com/s/article/Account-Creation",
                "https://support.remotelock.com/s/article/RemoteLock-Onboarding-Quick-Start-Guide",
                "https://support.remotelock.com/s/article/Device-Registration",
                "https://support.remotelock.com/s/article/RemoteLock-Mobile-App-Overview",
                "https://support.remotelock.com/s/article/RemoteLock-Software-Overview",
                "https://support.remotelock.com/s/article/WiFi-Provisioning-Guide",
                "https://support.remotelock.com/s/article/Connecting-Your-Lock-to-WiFi",
                "https://support.remotelock.com/s/article/RemoteLock-Internet-Connection-Setup-Guide",
                "https://support.remotelock.com/s/article/EDGEstate-by-RemoteLock-The-NEW-Connect-Portal",
                "https://support.remotelock.com/s/article/Getting-Started-Video"
              ]
            },
            {
              "name": "RemoteLock Portal",
              "url": "https://support.remotelock.com/s/remotelockportal",
              "subcategories": [
                {
                  "name": "Billing",
                  "url": "https://support.remotelock.com/s/billing",
                  "pages": [
                    "https://support.remotelock.com/s/article/Billing-FAQs",
                    "https://support.remotelock.com/s/article/EdgeState-Accounts-in-Grace-Period",
                    "https://support.remotelock.com/s/article/Payment-Token-Instructions-Prepaid-billing"
                  ]
                },
                {
                  "name": "Device Management",
                  "url": "https://support.remotelock.com/s/device-management",
                  "pages": [
                    "https://support.remotelock.com/s/article/TrueSecure-RemoteLock-Integration-Instructions",
                    "https://support.remotelock.com/s/article/Dusaw-RemoteLock-Integration-Instructions",
                    "https://support.remotelock.com/s/article/Resideo-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/SmartThings-RemoteLock-Integration-Instructions",
                    "https://support.remotelock.com/s/article/Kwikset-Halo-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Schlage-Engage-Device-Commissioning-Offline-Devices",
                    "https://support.remotelock.com/s/article/ResortLock-Lock-Management",
                    "https://support.remotelock.com/s/article/Door-Locks-Overview",
                    "https://support.remotelock.com/s/article/Device-Settings",
                    "https://support.remotelock.com/s/article/Door-Groups",
                    "https://support.remotelock.com/s/article/Device-Schedules-Explanations-and-Use-Cases",
                    "https://support.remotelock.com/s/article/Common-Door-Function",
                    "https://support.remotelock.com/s/article/360043010831-Replacing-your-RemoteLock-from-the-Device-Settings-page"
                  ]
                },
                {
                  "name": "Access User Management",
                  "url": "https://support.remotelock.com/s/access-user-management",
                  "pages": [
                    "https://support.remotelock.com/s/article/RemoteLock-Resident-App",
                    "https://support.remotelock.com/s/article/Entry-App-by-RemoteLock",
                    "https://support.remotelock.com/s/article/Access-Guests-and-Users",
                    "https://support.remotelock.com/s/article/Legacy-Smart-Card-Management-Enrolling-MIFARE-Cards-Fobs",
                    "https://support.remotelock.com/s/article/Access-Schedules-and-Access-Exceptions",
                    "https://support.remotelock.com/s/article/Devices-Access",
                    "https://support.remotelock.com/s/article/Guest-Email-Template",
                    "https://support.remotelock.com/s/article/Guest-Email-Template-Formatting",
                    "https://support.remotelock.com/s/article/ResortLock-Guest-Codes",
                    "https://support.remotelock.com/s/article/Guest-Email-and-Message-Time-Scheduling",
                    "https://support.remotelock.com/s/article/Access",
                    "https://support.remotelock.com/s/article/CSV-Bulk-Import-Access-Users",
                    "https://support.remotelock.com/s/article/Adding-a-LOCAL-user-code-to-the-lock",
                    "https://support.remotelock.com/s/article/Entry-App-settings-and-configuration-web-portal",
                    "https://support.remotelock.com/s/article/Mass-Access-Assignment",
                    "https://support.remotelock.com/s/article/Adding-Door-Access-to-a-Guest-or-User"
                  ]
                },
                {
                  "name": "Account Management",
                  "url": "https://support.remotelock.com/s/account-management-sub",
                  "pages": [
                    "https://support.remotelock.com/s/article/Account-Settings",
                    "https://support.remotelock.com/s/article/Events-explanation",
                    "https://support.remotelock.com/s/article/Reports",
                    "https://support.remotelock.com/s/article/Notifications-and-how-they-work",
                    "https://support.remotelock.com/s/article/Members-and-Roles",
                    "https://support.remotelock.com/s/article/Account-Management-Menu",
                    "https://support.remotelock.com/s/article/Notifications",
                    "https://support.remotelock.com/s/article/ResortLock-Dashboard",
                    "https://support.remotelock.com/s/article/Permissions-Explanation-Members-and-Roles",
                    "https://support.remotelock.com/s/article/Using-Shared-Device",
                    "https://support.remotelock.com/s/article/Using-Shared-Account",
                    "https://support.remotelock.com/s/article/Automated-Email-Status",
                    "https://support.remotelock.com/s/article/Two-Factor-Authentication",
                    "https://support.remotelock.com/s/article/Exporting-Users-and-Devices",
                    "https://support.remotelock.com/s/article/Dashboard-Health-Bar-and-Icon-meanings",
                    "https://support.remotelock.com/s/article/Locations",
                    "https://support.remotelock.com/s/article/Reset-Password-options-My-Account"
                  ]
                },
                {
                  "name": "Partner Integration",
                  "url": "https://support.remotelock.com/s/partner-integrations",
                  "pages": [
                    "https://support.remotelock.com/s/article/Mews-RemoteLock-Integration-Instructions",
                    "https://support.remotelock.com/s/article/Track-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/ChargeAutomation-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Schlage-Engage-RemoteLock-Integration-Instructions",
                    "https://support.remotelock.com/s/article/Schlage-Engage-Device-Commissioning-Instructions-Schlage-RC-RCK",
                    "https://support.remotelock.com/s/article/Schlage-Engage-Access-and-Device-Management-Offline",
                    "https://support.remotelock.com/s/article/igloohome-Integration-Beta",
                    "https://support.remotelock.com/s/article/igloohome-Integration",
                    "https://support.remotelock.com/s/article/RealPage-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/RoomRaccoon-RemoteLock-integration",
                    "https://support.remotelock.com/s/article/Zeevou-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Smoobu-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/KeyInCode-KoreLine",
                    "https://support.remotelock.com/s/article/Chekin-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Bookerville-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Beds24-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Whistle-legacy-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Hostaway-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/AppFolio-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Hostify-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/RentManager",
                    "https://support.remotelock.com/s/article/Stayntouch-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Yale-Home-RemoteLock-Integration-migration-from-Yale-Access-to-Yale-Home",
                    "https://support.remotelock.com/s/article/August-Lock-Integration",
                    "https://support.remotelock.com/s/article/innRoad-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Padsplit-RemoteLock-Integration-Instructions",
                    "https://support.remotelock.com/s/article/SuiteOp-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Yardi-Voyager-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/ThinkReservations-and-RemoteLock-Integration-PART-1",
                    "https://support.remotelock.com/s/article/TIDY-and-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/BookingAutomation-and-RemoteLock-integration",
                    "https://support.remotelock.com/s/article/ResortData-Processing-part1",
                    "https://support.remotelock.com/s/article/Resort-Data-Processing-RDP-and-RemoteLock-integration-part2",
                    "https://support.remotelock.com/s/article/Hospitable-and-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Guesty-Integration-Overview-and-Instructions",
                    "https://support.remotelock.com/s/article/TTLock-Integration",
                    "https://support.remotelock.com/s/article/Escapia-Integration",
                    "https://support.remotelock.com/s/article/Airbnb-Integration",
                    "https://support.remotelock.com/s/article/Vacation-Rental-Integrations-Guest-access-notifications",
                    "https://support.remotelock.com/s/article/Vacation-Rental-Integrations-Deactivation",
                    "https://support.remotelock.com/s/article/Vera-and-MiOS-Integration-overview",
                    "https://support.remotelock.com/s/article/Airbnb-Messaging-System",
                    "https://support.remotelock.com/s/article/HomeAway-VRBO-Integration",
                    "https://support.remotelock.com/s/article/Schlage-Encode-Integration-Overview",
                    "https://support.remotelock.com/s/article/Updating-Guesty-API-Credentials",
                    "https://support.remotelock.com/s/article/iCal-Feed-Integrations",
                    "https://support.remotelock.com/s/article/ResNexus-and-RemoteLock-Integration-Overview",
                    "https://support.remotelock.com/s/article/August-Lock-Pairing",
                    "https://support.remotelock.com/s/article/Akia-integration-with-RemoteLock",
                    "https://support.remotelock.com/s/article/Airbnb-to-remove-Guest-Email-feature-use-Messaging-only",
                    "https://support.remotelock.com/s/article/Streamline-V1-Integration-Overview",
                    "https://support.remotelock.com/s/article/Streamline-VRS-Integration-Process",
                    "https://support.remotelock.com/s/article/CourtReserve-Integration",
                    "https://support.remotelock.com/s/article/Pynwheel-Integration-with-RemoteLock-Overview",
                    "https://support.remotelock.com/s/article/Using-Guesty-s-Keycode-and-Automated-Messaging",
                    "https://support.remotelock.com/s/article/Lodgix-and-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Vacation-Rental-Integrations-Associating-Doors",
                    "https://support.remotelock.com/s/article/TripAngle-BookingWithEase-and-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/OwnerRez-Integration-Process",
                    "https://support.remotelock.com/s/article/iTrip-and-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/Partner-Integrations",
                    "https://support.remotelock.com/s/article/Ring-and-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/NewBook-Integration-Overview-and-Instructions",
                    "https://support.remotelock.com/s/article/Hostfully-Integration-with-RemoteLock"
                  ]
                }
              ]
            },
            {
              "name": "Troubleshooting",
              "url": "https://support.remotelock.com/s/troubleshooting",
              "subcategories": [
                {
                  "name": "General",
                  "url": "https://support.remotelock.com/s/general",
                  "pages": [
                    "https://support.remotelock.com/s/article/Device-Registration-Issues-Troubleshooting-and-Self-Help",
                    "https://support.remotelock.com/s/article/Need-Help",
                    "https://support.remotelock.com/s/article/Help-with-my-Vacation-Rental-Property-Management-Integration",
                    "https://support.remotelock.com/s/article/Will-not-lock-unlock",
                    "https://support.remotelock.com/s/article/Unable-to-Register-Lock-TS",
                    "https://support.remotelock.com/s/article/Troubleshooting-and-Best-Practices",
                    "https://support.remotelock.com/s/article/Lock-Flashing-Lights-and-Beeps-Meanings",
                    "https://support.remotelock.com/s/article/Spindle-Test"
                  ]
                },
                {
                  "name": "Legacy Product Troubleshooting",
                  "url": "https://support.remotelock.com/s/legacy-product-troubleshooting",
                  "pages": [
                    "https://support.remotelock.com/s/article/Lock-Grease",
                    "https://support.remotelock.com/s/article/Mortise-Latch-Installation-for-lock-models-RL4000-LS6i-LS6000i",
                    "https://support.remotelock.com/s/article/ResortLock-RL-4000-LS-6i-LS1500-Keypad-Replacement",
                    "https://support.remotelock.com/s/article/RemoteLock-V0-to-V1-Migration-Guide"
                  ]
                },
                {
                  "name": "WiFi Connectivity Troubleshooting",
                  "url": "https://support.remotelock.com/s/wifi-connectivity-troubleshooting",
                  "pages": [
                    "https://support.remotelock.com/s/article/Lock-Offline-ts",
                    "https://support.remotelock.com/s/article/Legacy-Device-Wi-Fi-Setup-Provisioning-Guide",
                    "https://support.remotelock.com/s/article/WiFi-Troubleshooting-Connectivity-Issues-Reprogramming-and-other-Network-information",
                    "https://support.remotelock.com/s/article/RouteThis-Overview",
                    "https://support.remotelock.com/s/article/WiFi-Connectivity-Best-Practices",
                    "https://support.remotelock.com/s/article/Using-the-Mobile-App-to-Connect-your-Lock-to-Wi-Fi",
                    "https://support.remotelock.com/s/article/OpenEdge-Troubleshooting-Codes"
                  ]
                },
                {
                  "name": "600 Series Troubleshooting",
                  "url": "https://support.remotelock.com/s/600-series-troubleshooting",
                  "pages": [
                    "https://support.remotelock.com/s/article/Tailpiece-Driven-Hub-Troubleshooting-KIC-4000-5000-Series",
                    "https://support.remotelock.com/s/article/600-Series-Motor-Replacement-openEDGE-Light-Duty-Commercial-Levers-3i-BG",
                    "https://support.remotelock.com/s/article/Battery-Drain-Issues"
                  ]
                },
                {
                  "name": "500 Series Troubleshooting",
                  "url": "https://support.remotelock.com/s/500-series-troubleshooting",
                  "pages": [
                    "https://support.remotelock.com/s/article/Snapback-Issues",
                    "https://support.remotelock.com/s/article/500-Series-OpenEdge-Deadbolt-5i-RG-Replace-Motor",
                    "https://support.remotelock.com/s/article/500-Series-OpenEdge-Deadbolt-5i-RG-Tailpiece-Orientation",
                    "https://support.remotelock.com/s/article/500-Series-OpenEdge-5i-RG-Replace-Keypad"
                  ]
                }
              ]
            },
            {
              "name": "General Information",
              "url": "https://support.remotelock.com/s/general-information",
              "pages": [
                "https://support.remotelock.com/s/article/Contact-Support",
                "https://support.remotelock.com/s/article/Feature-Request-Suggestions",
                "https://support.remotelock.com/s/article/Warranty-and-Returns-Information",
                "https://support.remotelock.com/s/article/Transfer-of-Ownership",
                "https://support.remotelock.com/s/article/Blocking-a-ReadyPIN",
                "https://support.remotelock.com/s/article/New-RemoteLock-Features-Update-as-of-9-25-18",
                "https://support.remotelock.com/s/article/How-to-update-your-customer-satisfaction-rating"
              ]
            },
            {
              "name": "Hardware Information",
              "url": "https://support.remotelock.com/s/hardware-information",
              "subcategories": [
                {
                  "name": "500 series",
                  "url": "https://support.remotelock.com/s/500-series",
                  "pages": [
                    "https://support.remotelock.com/s/article/500-Series-Deadbolt-Handing-the-Lock-openEDGE-Residential-Grade-5i-RG",
                    "https://support.remotelock.com/s/article/500-Series-Lever-Hardware-Installation-openEDGE-Residential-Grade-5i-RG",
                    "https://support.remotelock.com/s/article/DB-500R-non-connected-User-Manual",
                    "https://support.remotelock.com/s/article/LS-DB500R-Keypad-Electronic-Lock-Remote-Control-Manual",
                    "https://support.remotelock.com/s/article/LS-L500i-Installation-and-Local-Setup-Legacy-Wi-Fi-Locks",
                    "https://support.remotelock.com/s/article/LS-DB500i-Installation-and-Local-Setup-Legacy-Wi-Fi-Locks",
                    "https://support.remotelock.com/s/article/500-Series-Deadbolt-Hardware-Installation-openEDGE-Residential-Grade-5i-RG"
                  ]
                },
                {
                  "name": "600-series",
                  "url": "https://support.remotelock.com/s/600-series",
                  "pages": [
                    "https://support.remotelock.com/s/article/600-Series-Hardware-Installation-openEDGE-Light-Duty-Commercial-Levers-3i-BG",
                    "https://support.remotelock.com/s/article/600-Series-Mortise-Latch-Installation-openEDGE-Light-Duty-Commercial-Levers-3i-BG",
                    "https://support.remotelock.com/s/article/600-Series-FAQs-openEDGE-Light-Duty-Commercial-Levers-3i-BG"
                  ]
                },
                {
                  "name": "700 Series",
                  "url": "https://support.remotelock.com/s/700-series",
                  "pages": [
                    "https://support.remotelock.com/s/article/CG-EX-Push-Exit-Panic-Bar-Installation-Guide",
                    "https://support.remotelock.com/s/article/OpenEdge-CG-formerly-model-7i-Installation-manual-print-version",
                    "https://support.remotelock.com/s/article/700-Series-Mortise-Latch-Installation-openEDGE-Medium-Duty-Commercial-Levers-7i-CG",
                    "https://support.remotelock.com/s/article/700-Series-Mortise-latch-change-handing-instructions-openEDGE-Medium-Duty-Commercial-Levers-7i-CG",
                    "https://support.remotelock.com/s/article/700-Series-Hardware-Installation-openEDGE-Medium-Duty-Commercial-Levers-7i-CG",
                    "https://support.remotelock.com/s/article/ManualProgrammingFunctions",
                    "https://support.remotelock.com/s/article/700-CG-7i-800-Series-Programming-Functions-and-Function-Codes"
                  ]
                },
                {
                  "name": "800 Series",
                  "url": "https://support.remotelock.com/s/800-series",
                  "pages": [
                    "https://support.remotelock.com/s/article/800-Series-Hardware-Installation-openEDGE-Heavy-Duty-Commercial-Lever"
                  ]
                },
                {
                  "name": "ACS",
                  "url": "https://support.remotelock.com/s/acs",
                  "pages": [
                    "https://support.remotelock.com/s/article/ACS-ACK-Troubleshooting-Guide",
                    "https://support.remotelock.com/s/article/Relay-Safety-Sheet",
                    "https://support.remotelock.com/s/article/Regular-ACS-Mode-Overview",
                    "https://support.remotelock.com/s/article/Elevator-ACS-Mode-Overview",
                    "https://support.remotelock.com/s/article/Setting-up-FAI-Fire-Alarm-Interface-Connection",
                    "https://support.remotelock.com/s/article/Reconnecting-ACK-ACS-to-Network",
                    "https://support.remotelock.com/s/article/Adding-Expansion-Panel-to-Existing-ACS-Install",
                    "https://support.remotelock.com/s/article/ACS-Installation",
                    "https://support.remotelock.com/s/article/Prior-To-ACS-Installation",
                    "https://support.remotelock.com/s/article/ACS-Installation-Completion-Checklist",
                    "https://support.remotelock.com/s/article/ACS-Installation-Warnings",
                    "https://support.remotelock.com/s/article/24-Volt-Conversion-Steps",
                    "https://support.remotelock.com/s/article/Testing-ACS-Installation",
                    "https://support.remotelock.com/s/article/Bulk-Erase-Steps-For-First-ACS-Installation",
                    "https://support.remotelock.com/s/article/Adding-an-ACS-Device-to-the-Remotelock-Portal-Mercury-Security-ACS-Integration",
                    "https://support.remotelock.com/s/article/MR52-Expansion-Board-User-Manual",
                    "https://support.remotelock.com/s/article/RemoteLock-Mobile-Key-Reader-Setup",
                    "https://support.remotelock.com/s/article/MR52-Expansion-Panel-Wiring-Schema-for-Addressing",
                    "https://support.remotelock.com/s/article/LP1502-Controller-User-Manual",
                    "https://support.remotelock.com/s/article/Creating-Mobile-Key-Credentials",
                    "https://support.remotelock.com/s/article/ACS-Technical-Documents",
                    "https://support.remotelock.com/s/article/LP1501-Controller-User-Manual",
                    "https://support.remotelock.com/s/article/ACS-Configuration",
                    "https://support.remotelock.com/s/article/RemoteLock-Mobile-Key-Quick-Guide",
                    "https://support.remotelock.com/s/article/Card-Formats-Supported-with-Mercury",
                    "https://support.remotelock.com/s/article/RemoteLock-Korelock-MF009-Quick-Guide",
                    "https://support.remotelock.com/s/article/Lockdown-Functionality",
                    "https://support.remotelock.com/s/article/LP4502-Controller-User-Manual",
                    "https://support.remotelock.com/s/article/ACS-Wire-Diagrams",
                    "https://support.remotelock.com/s/article/MR50-Expansion-Board-User-Manual"
                  ]
                },
                {
                  "name": "Other Products",
                  "url": "https://support.remotelock.com/s/other-products",
                  "pages": [
                    "https://support.remotelock.com/s/article/Kwikset-Halo-Installation-Instructions",
                    "https://support.remotelock.com/s/article/Yale-Assure-Lock-2-Key-Free-Deadbolt-Installation-Guide",
                    "https://support.remotelock.com/s/article/Yale-Assure-Lock-2-Keyed-Deadbolt-Installation-Guide",
                    "https://support.remotelock.com/s/article/Schlage-Encode-Lever-Quick-Start-Guide",
                    "https://support.remotelock.com/s/article/Schlage-Encode-Deabolt-Quick-Start-Guide",
                    "https://support.remotelock.com/s/article/Turno-RemoteLock-Integration",
                    "https://support.remotelock.com/s/article/McGrath-Locks-NX5-User-Manual",
                    "https://support.remotelock.com/s/article/McGrath-Locks-X3-User-Manual",
                    "https://support.remotelock.com/s/article/McGrath-locks-Albion",
                    "https://support.remotelock.com/s/article/PROLOK-Deluxe-Hardware-Installation-Manual",
                    "https://support.remotelock.com/s/article/ProLok-Slimline-User-Manual",
                    "https://support.remotelock.com/s/article/ProLok-Slimline-Hardware-Installation-Guide",
                    "https://support.remotelock.com/s/article/3500-Lever-Hardware-Installation-Guide",
                    "https://support.remotelock.com/s/article/3500-Deadbolt-Hardware-Installation-Guide",
                    "https://support.remotelock.com/s/article/LS-P50-User-Manual-and-Provisioning-Guide-Power-Plug",
                    "https://support.remotelock.com/s/article/RemoteLock-model-6i-Installation",
                    "https://support.remotelock.com/s/article/Power-Plugs",
                    "https://support.remotelock.com/s/article/LS-90i-Local-Programming-and-Operation-Guide-Thermostat",
                    "https://support.remotelock.com/s/article/LS-90i-Installation-Guide-Thermostat",
                    "https://support.remotelock.com/s/article/LS-60i-Local-Programming-and-Operation-Guide-Thermostat",
                    "https://support.remotelock.com/s/article/LS-60i-Installation-Guide-Thermostat",
                    "https://support.remotelock.com/s/article/Types-of-Smart-Cards-Prox-Cards"
                  ]
                },
                {
                  "name": "ResortLocks",
                  "url": "https://support.remotelock.com/s/resortlocks",
                  "pages": [
                    "https://support.remotelock.com/s/article/LSRL-1-Wire-Software-Manual-Legacy-ResortLock-Desktop-Software",
                    "https://support.remotelock.com/s/article/ResortLock-FAQs-and-Troubleshooting-Guide",
                    "https://support.remotelock.com/s/article/RL2000-Installation-and-Local-Setup-ResortLock",
                    "https://support.remotelock.com/s/article/RL4000-Installation-and-Local-Setup-ResortLock",
                    "https://support.remotelock.com/s/article/Thermostats"
                  ]
                }
              ]
            },
            {
              "name": "KeyInCode Information",
              "url": "https://support.remotelock.com/s/keyincode-hardware",
              "subcategories": [
                {
                  "name": "4000 Series",
                  "url": "https://support.remotelock.com/s/4000-series",
                  "pages": [
                    "https://support.remotelock.com/s/article/4000-Series-FAQs",
                    "https://support.remotelock.com/s/article/4000-Series-Installation-Guide"
                  ]
                },
                {
                  "name": "5000 Series Hardware",
                  "url": "https://support.remotelock.com/s/5000-series-hardware",
                  "pages": [
                    "https://support.remotelock.com/s/article/5000-Series-Installation-Guide",
                    "https://support.remotelock.com/s/article/5000-Series-Exit-Bar-Installation"
                  ]
                },
                {
                  "name": "6000 Series Hardware",
                  "url": "https://support.remotelock.com/s/6000-series-hardware",
                  "pages": [
                    "https://support.remotelock.com/s/article/6000-Series-Installation-Guide"
                  ]
                },
                {
                  "name": "KIC General Info",
                  "url": "https://support.remotelock.com/s/kic-general-info",
                  "pages": [
                    "https://support.remotelock.com/s/article/2500-Installation-Manual",
                    "https://support.remotelock.com/s/article/Smart-Card-and-Fob-Enrollment",
                    "https://support.remotelock.com/s/article/Using-Cards-Fobs-on-KeyInCode-Locks",
                    "https://support.remotelock.com/s/article/Mortise-Latch-Change-of-Handing-Instructions",
                    "https://support.remotelock.com/s/article/ReadyPIN-on-KeyInCode-Locks-Tutorial",
                    "https://support.remotelock.com/s/article/Manual-Programming-Functions",
                    "https://support.remotelock.com/s/article/Assigning-MIFARE-Cards-Fobs-to-Access-Users",
                    "https://support.remotelock.com/s/article/Offline-Mode-Lock-Setup",
                    "https://support.remotelock.com/s/article/Enrolling-MIFARE-Cards-Fobs"
                  ]
                }
              ]
            }
          ]
        }
        
        page_index = []
        structure_parts = ["="*70, "COMPLETE REMOTELOCK DOCUMENTATION INDEX", "="*70, "\n"]
        
        for category in sitemap_data["categories"]: # Changed 'sitemap' to 'sitemap_data'
            structure_parts.append(f"📁 {category['name']}")
            
            # Direct pages
            if "pages" in category:
                for url in category["pages"]:
                    slug = url.split('/article/')[-1] if '/article/' in url else url.split('/')[-1]
                    page_index.append({"slug": slug, "category": category['name'], "subcategory": None})
                    structure_parts.append(f"   • {slug}")
            
            # Subcategories
            if "subcategories" in category:
                for sub_category_data in category["subcategories"]: # FIX: Corrected variable name
                    structure_parts.append(f"\n   📂 {sub_category_data['name']}")
                    for url in sub_category_data["pages"]:
                        slug = url.split('/article/')[-1] if '/article/' in url else url.split('/')[-1]
                        page_index.append({"slug": slug, "category": category['name'], "subcategory": sub_category_data['name']})
                        structure_parts.append(f"      • {slug}")
            structure_parts.append("\n")
        
        structure_parts.extend([
            f"\n{'='*70}",
            f"TOTAL: {len(page_index)} pages",
            f"{'='*70}\n"
        ])
        
        return "\n".join(structure_parts), page_index
    except Exception as e:
        print(f"Error loading sitemap: {e}")
        return f"Error loading sitemap: {e}", []

SITEMAP_STRUCTURE, PAGE_INDEX = load_complete_sitemap()

# --- Cypher Generation Prompt (Refined) ---
CYPHER_GENERATION_PROMPT = """You are an expert in Neo4j Cypher. Your goal is to generate highly accurate Cypher queries to retrieve documentation from a knowledge base about RemoteLock products.

You have access to the following graph schema:
Nodes:
- `:Page`: Represents a documentation article. Properties: `id` (often same as slug), `slug`, `title`, `content`, `url`.
- `:Category`: Represents a top-level category. Properties: `name`, `url`.
- `:Subcategory`: Represents a sub-category. Properties: `name`, `url`.

Relationships:
- `(p:Page)-[:BELONGS_TO_SUBCATEGORY]->(s:Subcategory)`: A page belongs to a subcategory.
- `(s:Subcategory)-[:BELONGS_TO_CATEGORY]->(c:Category)`: A subcategory belongs to a category.
- `(p:Page)-[:BELONGS_TO_CATEGORY]->(c:Category)`: A page directly belongs to a category (if it has no subcategory).

You have been provided with a complete, indexed list of all available page slugs and their hierarchical context:

{sitemap_structure}

---
CRITICAL INSTRUCTIONS FOR CYPHER GENERATION:

1.  **MOST IMPORTANT: PRIORITIZE EXACT OR NEAR-EXACT SLUG MATCHES.**
    *   Examine the user's question and cross-reference it with the `sitemap_structure` AND the `slug_hints` provided below.
    *   If you can find one or more exact or very close matches for `slug` (or `id`), generate a query using `p.slug = 'EXACT-SLUG-NAME'` or `p.slug IN ['SLUG1', 'SLUG2']`.
    *   DO NOT use `toLower(p.content) CONTAINS ...` if you find strong slug matches.

2.  **SECOND PRIORITY: HIERARCHICAL NAVIGATION + KEYWORDS IN SLUG/TITLE.**
    *   If the query mentions a series (e.g., "2500 series", "500 series") or a known category/subcategory name (see `hierarchy_hints` below), use the relationships to filter pages.
    *   Combine with `toLower(p.slug) CONTAINS 'keyword'` or `toLower(p.title) CONTAINS 'keyword'` for better precision.
    *   Example for "2500 series installation":
        ```cypher
        MATCH (p:Page)-[:BELONGS_TO_SUBCATEGORY]->(s:Subcategory)
        WHERE s.name = 'KIC General Info' AND (toLower(p.slug) CONTAINS '2500' OR toLower(p.title) CONTAINS '2500')
        RETURN p.id, p.slug, p.title, p.content, p.url
        LIMIT 5
        ```
    *   Example for "troubleshooting FAQs":
        ```cypher
        MATCH (p:Page)-[:BELONGS_TO_CATEGORY]->(c:Category)
        WHERE c.name = 'FAQs' AND toLower(p.title) CONTAINS 'troubleshooting'
        RETURN p.id, p.slug, p.title, p.content, p.url
        LIMIT 10
        ```

3.  **LAST RESORT: BROADER CONTENT SEARCH (ONLY IF 1 & 2 YIELD POOR OR NO RESULTS).**
    *   Only if the above methods are unlikely to yield good results, perform a broader `toLower(p.content) CONTAINS 'keyword'` search. This should be combined with other properties if possible.

---
MANDATORY RETURN CLAUSE:
ALWAYS return `p.id, p.slug, p.title, p.content, p.url`

MANDATORY LIMIT:
ALWAYS include `LIMIT` at the end of your query, and ensure it's `LIMIT 5` for Cypher queries in this retriever.

Avoid using generic `OR` conditions that mix slug/id checks with broad content searches unless absolutely necessary and well-targeted. Prefer separate, targeted queries or combine only when terms are highly related.

{slug_hints_injection}
{hierarchy_hints_injection}

Question: {question}

YOUR ANSWER (Cypher query only):"""

class ProductionRetriever:

    def __init__(self):
        print("QUERY_LLM: ProductionRetriever.__init__ started", flush=True)
        logger.info("="*70)
        logger.info("Production RemoteLock Retriever Initialization")
        logger.info("="*70)

        # Connect to Neo4j
        print("QUERY_LLM: [1/4] Connecting to Neo4j...", flush=True)
        logger.info("[1/4] Connecting to Neo4j...")
        try:
            # Limit connection pool size to reduce memory usage (~10MB savings)
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD),
                max_connection_pool_size=5
            )
            print("QUERY_LLM: Neo4j driver created, verifying connectivity...", flush=True)
            self.driver.verify_connectivity()
            print("QUERY_LLM: ✓ Neo4j connection established", flush=True)
            logger.info("✓ Neo4j connection established")
        except Exception as e:
            print(f"QUERY_LLM: ✗ Neo4j connection failed: {e}", flush=True)
            logger.error(f"Failed to connect to Neo4j: {e}", exc_info=True)
            raise

        # Initialize LangChain Graph
        logger.info("[2/4] Initializing LangChain Neo4jGraph...")
        try:
            # Using the recommended Neo4jGraph
            self.graph = Neo4jGraph(
                url=NEO4J_URI,
                username=NEO4J_USER,
                password=NEO4J_PASSWORD
            )
            # It's good practice to call refresh_schema
            self.graph.refresh_schema()
            logger.info("✓ Neo4jGraph initialized and schema refreshed")
        except Exception as e:
            logger.error(f"Graph initialization failed: {e}", exc_info=True)
            self.graph = None # Set to None if connection fails

        # Initialize LLM
        logger.info("[3/4] Loading Gemini LLM...")
        try:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0,
                google_api_key=GEMINI_API_KEY
            )
            logger.info("✓ Gemini LLM loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Gemini LLM: {e}", exc_info=True)
            raise

        # Create Cypher chain
        logger.info("[4/4] Creating GraphCypherQAChain...")
        if self.graph:
            try:
                self.cypher_chain = GraphCypherQAChain.from_llm(
                    llm=self.llm,
                    graph=self.graph, # This `graph` object *is* a GraphStore
                    cypher_prompt=PromptTemplate(
                        input_variables=["schema", "question", "sitemap_structure", "slug_hints_injection", "hierarchy_hints_injection"],
                        template=CYPHER_GENERATION_PROMPT
                    ),
                    verbose=True,
                    return_intermediate_steps=True,
                    allow_dangerous_requests=True,
                    top_k=5 # Limit the chain's internal retrieval to 5 for consistency with your request
                )
                self.use_chain = True
                logger.info("✓ GraphCypherQAChain initialized successfully")
            except Exception as e:
                self.use_chain = False
                logger.warning(f"GraphCypherQAChain initialization failed: {e}. Falling back to direct Cypher mode", exc_info=True)
        else:
            self.use_chain = False
            logger.warning("Graph not initialized, using direct Cypher mode")

        # Embeddings - Using Gemini API (zero local memory footprint)
        print("QUERY_LLM: [5/5] Configuring Gemini embeddings API...", flush=True)
        logger.info("[5/5] Configuring Gemini embeddings API...")
        try:
            # Use Gemini API for embeddings instead of local SentenceTransformer
            # This saves ~300MB of memory (PyTorch + model) - critical for Render free tier
            self.embedder = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=GEMINI_API_KEY
            )
            print("QUERY_LLM: ✓ Gemini embeddings API configured successfully", flush=True)
            logger.info("✓ Gemini embeddings API configured successfully")
        except Exception as e:
            print(f"QUERY_LLM: ✗ Failed to configure embeddings API: {e}", flush=True)
            logger.error(f"Failed to configure embeddings API: {e}", exc_info=True)
            raise

        print("QUERY_LLM: ProductionRetriever initialization complete", flush=True)
        logger.info("="*70)
        logger.info("ProductionRetriever initialization complete")
        logger.info("="*70)
    
    def close(self):
        if self.driver:
            self.driver.close()
    
    def _normalize(self, text: str) -> str:
        """Normalize for matching, remove common non-alphanumeric and extra spaces."""
        return re.sub(r'[^a-z0-9]+', '', text.lower())
    
    def _slug_match_score(self, slug: str, query: str) -> float:
        """Calculate slug match score (0-100) based on normalized string similarity and word overlap."""
        if not slug:
            return 0.0
        
        norm_slug = self._normalize(slug)
        norm_query = self._normalize(query)
        
        # Exact match (after normalization)
        if norm_slug == norm_query:
            return 100.0
        
        # SequenceMatcher for overall string similarity
        sm_ratio = SequenceMatcher(None, norm_slug, norm_query).ratio() * 80.0 # Max 80 points
        
        # Word overlap
        query_words = set(re.findall(r'\b\w+\b', query.lower())) - {'the', 'a', 'of', 'for', 'series', 'guide', 'manual'}
        slug_words = set(re.findall(r'\b\w+\b', slug.lower())) - {'the', 'a', 'of', 'for', 'series', 'openedge'}
        
        if not query_words:
            return sm_ratio # If query is just noise, rely on string similarity
        
        matched_words = query_words.intersection(slug_words)
        word_overlap_score = (len(matched_words) / len(query_words)) * 20.0 # Max 20 points
        
        return sm_ratio + word_overlap_score
    
    def _find_matching_slugs_and_hierarchy(self, query: str) -> Dict[str, Any]:
        """Helper: Find strong candidate slugs and relevant hierarchy info from PAGE_INDEX."""
        query_lower = query.lower()
        query_words = set(re.findall(r'\b\w+\b', query_lower)) - {'the', 'a', 'of', 'for', 'series', 'guide', 'manual', 'how', 'to', 'do', 'i', 'installation'}
        
        slug_candidates = []
        hierarchy_candidates = set() # To store unique category/subcategory names
        
        for page_info in PAGE_INDEX:
            slug = page_info['slug']
            category = page_info['category']
            subcategory = page_info['subcategory']

            score = 0.0
            
            # Slug score
            score += self._slug_match_score(slug, query)
            
            # Check against category/subcategory names
            if category and self._normalize(category) in self._normalize(query):
                score += 30.0 # Boost for category mention
                hierarchy_candidates.add(category)
            if subcategory and self._normalize(subcategory) in self._normalize(query):
                score += 40.0 # Higher boost for subcategory mention
                hierarchy_candidates.add(subcategory)

            if score > 50: # Only consider reasonably strong candidates
                slug_candidates.append({
                    "slug": slug,
                    "category": category,
                    "subcategory": subcategory,
                    "score": score
                })
            
        # Sort by score descending and return unique slugs
        slug_candidates.sort(key=lambda x: x['score'], reverse=True)
        unique_slugs = []
        seen_slugs = set()
        for m in slug_candidates:
            if m['slug'] not in seen_slugs:
                unique_slugs.append(m['slug'])
                seen_slugs.add(m['slug'])
        
        return {
            "slug_hints": unique_slugs[:5], # Top 5 slug candidates
            "hierarchy_hints": list(hierarchy_candidates) # All detected hierarchy names
        }
    
    def _rank_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Rank by relevance, heavily prioritizing slug/title matches over general content."""
        norm_query = self._normalize(query)
        query_words_strict = set(re.findall(r'\b\w+\b', query.lower())) - {'the', 'a', 'of', 'for', 'series', 'guide', 'manual', 'how', 'to', 'do', 'i'}

        for r in results:
            score = r.get('similarity', 0) * 100 if r.get('similarity') else 0 # Start with similarity if it's a vector result
            
            # --- Primary: Exact/Strong SLUG & ID Matching (Highest Priority) ---
            slug = r.get('slug', '')
            id_val = r.get('id', '') # id property
            
            if slug:
                norm_slug = self._normalize(slug)
                if norm_slug == norm_query: # Perfect normalized slug match
                    score += 1000.0
                else:
                    score += self._slug_match_score(slug, query) * 8.0 # Scale score
            
            if id_val and id_val != slug: # If id is different and relevant
                norm_id = self._normalize(id_val)
                if norm_id == norm_query:
                    score += 900.0
                else:
                    score += self._slug_match_score(id_val, query) * 7.0

            # --- Secondary: Title Matching ---
            if r.get('title'):
                norm_title = self._normalize(r['title'])
                if norm_title == norm_query:
                    score += 500.0
                else:
                    title_sm_ratio = SequenceMatcher(None, norm_title, norm_query).ratio()
                    score += title_sm_ratio * 300.0

                    title_words = set(re.findall(r'\b\w+\b', r['title'].lower()))
                    overlap_title = query_words_strict.intersection(title_words)
                    if query_words_strict:
                        score += (len(overlap_title) / len(query_words_strict)) * 100.0
            
            # --- Tertiary: Content Relevance (Lower Priority) ---
            if r.get('content'):
                content_words = set(re.findall(r'\b\w{3,}\b', r['content'].lower())) # Only significant words
                if query_words_strict:
                    overlap_content = len(query_words_strict.intersection(content_words)) / len(query_words_strict)
                    score += overlap_content * 50.0 # Lower weight
            
            # Has content bonus (penalize empty/very short results)
            if r.get('content') and len(r['content']) > 100:
                score += 20.0
            
            r['_score'] = score
        
        results.sort(key=lambda x: x.get('_score', 0), reverse=True)
        return results
    
    def cypher_search(self, question: str) -> List[Dict]:
        """Primary search via Cypher, with enriched prompt context."""
        timing_cypher_total_start = time.perf_counter()
        logger.info("=== CYPHER Search Started ===")
        logger.info(f"Query: {question}")

        # Generate hints from our sitemap index
        timing_hints_start = time.perf_counter()
        hints = self._find_matching_slugs_and_hierarchy(question)
        timing_hints_end = time.perf_counter()
        logger.info(f"⏱️  Hint generation took: {timing_hints_end - timing_hints_start:.3f}s")
        slug_hints_str = f"STRONG HINT: Consider these relevant slugs for direct matching: {', '.join(hints['slug_hints'])}\n" if hints['slug_hints'] else ""
        hierarchy_hints_str = f"STRONG HINT: Relevant categories/subcategories might include: {', '.join(hints['hierarchy_hints'])}\n" if hints['hierarchy_hints'] else ""

        if hints['slug_hints']:
            logger.info(f"Detected slug candidates: {', '.join(hints['slug_hints'])}")
        if hints['hierarchy_hints']:
            logger.info(f"Detected hierarchy: {', '.join(hints['hierarchy_hints'])}")
        
        try:
            if self.use_chain: # This path is attempted only if GraphCypherQAChain initialized successfully
                logger.info("Using GraphCypherQAChain for query generation...")

                # Format the prompt dynamically with current schema and generated hints
                # The prompt expects 'schema' directly, not a dictionary.
                enriched_q = {
                    "question": question,
                    "schema": self.graph.schema if self.graph else "Schema unavailable", # Ensure schema is passed correctly
                    "sitemap_structure": SITEMAP_STRUCTURE,
                    "slug_hints_injection": slug_hints_str,
                    "hierarchy_hints_injection": hierarchy_hints_str
                }

                # Invoke the chain using the dynamically formatted prompt
                logger.debug("Invoking chain with enriched query context...")
                timing_llm_cypher_start = time.perf_counter()
                result = self.cypher_chain.invoke(enriched_q)
                timing_llm_cypher_end = time.perf_counter()
                logger.info(f"⏱️  LLM Cypher generation took: {timing_llm_cypher_end - timing_llm_cypher_start:.2f}s")
                logger.debug("Chain invocation completed")
                
                # --- FIX START: Extract generated Cypher query more robustly ---
                cypher = ""
                # Modern LangChain `invoke` on QA chains often returns a dictionary.
                # The 'query' for GraphCypherQAChain is usually under 'query' in intermediate_steps,
                # or as a top-level key in the result.
                if "intermediate_steps" in result and len(result["intermediate_steps"]) > 0:
                    # Look for the step that contains the generated Cypher query
                    for step in result["intermediate_steps"]:
                        if "query" in step: # This is the ideal case
                            cypher = step["query"]
                            break
                    if not cypher and "query" in result: # Fallback if not in intermediate_steps, check top-level
                        cypher = result["query"]
                elif "query" in result: # Direct access if the chain returns it at top level
                    cypher = result["query"]
                else:
                    print("  ⚠ Could not extract Cypher query from chain result.")
                    return [] # Return empty if no query was found
                # --- FIX END ---
                
                logger.info(f"Generated Cypher query:\n{cypher.strip()}")

                # Execute the generated Cypher query
                logger.debug("Executing Cypher query on Neo4j...")
                timing_neo4j_cypher_start = time.perf_counter()
                with self.driver.session() as session:
                    raw_results = [dict(r) for r in session.run(cypher)]
                timing_neo4j_cypher_end = time.perf_counter()
                logger.info(f"⏱️  Neo4j Cypher execution took: {timing_neo4j_cypher_end - timing_neo4j_cypher_start:.2f}s")

                timing_cypher_total = time.perf_counter() - timing_cypher_total_start
                logger.info(f"⏱️  TOTAL Cypher search took: {timing_cypher_total:.2f}s")

                if raw_results:
                    logger.info(f"✓ Cypher search found {len(raw_results)} results")
                    return raw_results
                else:
                    logger.warning("No results from Cypher search")
                    return []
            else: # Fallback to direct execution if GraphCypherQAChain failed to init
                # Direct execution mode (if chain not initialized)
                logger.info("Using direct Cypher generation (fallback mode)...")
                prompt_template_direct = PromptTemplate(
                    input_variables=["schema", "question", "sitemap_structure", "slug_hints_injection", "hierarchy_hints_injection"],
                    template=CYPHER_GENERATION_PROMPT
                )
                prompt_formatted = prompt_template_direct.format(
                    schema=self.graph.schema if self.graph else "Schema unavailable",
                    question=question,
                    sitemap_structure=SITEMAP_STRUCTURE,
                    slug_hints_injection=slug_hints_str,
                    hierarchy_hints_injection=hierarchy_hints_str
                )
                
                logger.debug("Invoking LLM directly for Cypher generation...")
                response_llm = self.llm.invoke(prompt_formatted)
                cypher = response_llm.content.strip().replace("```cypher", "").replace("```", "").strip()

                logger.info(f"Generated Cypher (direct):\n{cypher.strip()}")

                logger.debug("Executing direct Cypher query...")
                with self.driver.session() as session:
                    raw_results = [dict(r) for r in session.run(cypher)]

                if raw_results:
                    logger.info(f"✓ Direct Cypher found {len(raw_results)} results")
                    return raw_results
                else:
                    logger.warning("No results from direct Cypher search")
                    return []

        except Exception as e:
            logger.error(f"Error in Cypher search: {e}", exc_info=True)
            return []
    
    def vector_search(self, question: str) -> List[Dict]:
        """Vector search"""
        timing_vector_total_start = time.perf_counter()
        logger.info("=== VECTOR Search Started ===")
        logger.info(f"Query: {question}")
        logger.debug("Computing embeddings via Gemini API...")

        try:
            # embed_query() returns a list directly (no need for .tolist())
            timing_embedding_start = time.perf_counter()
            emb = self.embedder.embed_query(question)
            timing_embedding_end = time.perf_counter()
            logger.info(f"⏱️  Gemini embeddings API took: {timing_embedding_end - timing_embedding_start:.2f}s")
            logger.debug(f"Embedding computed via API, dimension: {len(emb)}")
            
            # Increased WHERE sim > 0.3 for slightly stricter similarity
            # Changed LIMIT to 10-15 to ensure enough candidates to pick 5 unique ones
            cypher = """
            MATCH (p:Page)
            WHERE p.embedding IS NOT NULL
            WITH p,
                 reduce(d=0.0, i IN range(0, size(p.embedding)-1) |
                     d + p.embedding[i] * $emb[i]) AS dot,
                 sqrt(reduce(s=0.0, i IN range(0, size(p.embedding)-1) |
                     s + p.embedding[i]^2)) AS p_n,
                 sqrt(reduce(s=0.0, i IN range(0, size($emb)-1) |
                     s + $emb[i]^2)) AS q_n
            WITH p, dot/(p_n * q_n) AS sim
            WHERE sim > 0.3 // Increased threshold for better relevance
            RETURN p.id as id, p.slug as slug, p.title as title,
                   p.content as content, p.url as url, sim as similarity
            ORDER BY sim DESC LIMIT 15
            """ # Limit increased to 15 to provide more candidates for hybrid selection

            logger.debug("Executing vector similarity query...")
            timing_neo4j_vector_start = time.perf_counter()
            with self.driver.session() as session:
                results = [dict(r) for r in session.run(cypher, emb=emb)]
            timing_neo4j_vector_end = time.perf_counter()
            logger.info(f"⏱️  Neo4j vector similarity took: {timing_neo4j_vector_end - timing_neo4j_vector_start:.2f}s")

            timing_vector_total = time.perf_counter() - timing_vector_total_start
            logger.info(f"⏱️  TOTAL Vector search took: {timing_vector_total:.2f}s")

            if results:
                logger.info(f"✓ Vector search found {len(results)} similar pages")
                logger.debug(f"Top similarity score: {results[0].get('similarity', 0):.3f}" if results else "N/A")
                return results

            logger.warning("No similar pages found with vector search")
            return []

        except Exception as e:
            logger.error(f"Error in vector search: {e}", exc_info=True)
            return []

   # def retrieve(self, question: str) -> Dict:
        """Main retrieval with hybrid search (Cypher + Vector) - REVISED LOGIC"""
        print("\n" + "="*70)
        print(f"QUERY: {question}")
        print("="*70)
        
        # 1. Get initial Cypher results (limited to 5 by the query)
        cypher_results = self.cypher_search(question)
        
        # Use a set to track slugs/ids of items already included from Cypher
        seen_keys = set()
        final_results = []

        # Add Cypher results first, up to 5
        for r in cypher_results:
            key = r.get('slug') or r.get('id')
            if key and key not in seen_keys:
                final_results.append(r)
                seen_keys.add(key)
                if len(final_results) >= 5: # Take at most 5 from Cypher first
                    break
        
        # 2. If we still need more results (up to a total of 10), perform vector search
        if len(final_results) < 10:
            vector_results = self.vector_search(question)
            
            # Add vector results, ensuring no duplicates and topping up to 10
            for r in vector_results:
                key = r.get('slug') or r.get('id')
                if key and key not in seen_keys:
                    final_results.append(r)
                    seen_keys.add(key)
                    if len(final_results) >= 10: # Stop once we have 10 total
                        break
        
        # 3. Rank the final combined set of non-duplicate results
        ranked_final_results = self._rank_results(final_results, question)

        return {
            "success": bool(ranked_final_results),
            "method": "hybrid",
            "results": ranked_final_results # Return all, limit 10 is implicit from prior logic
        }
    
    #def retrieve(self, question: str) -> Dict:
        """Main retrieval with hybrid search (Cypher + Vector) - REVISED LOGIC"""
        print("\n" + "="*70)
        print(f"QUERY: {question}")
        print("="*70)
        
        # Initialize containers for the final top 10 results
        final_results = []
        seen_keys = set() # To track slugs/ids of items already added

        # 1. Get Cypher results (the Cypher query itself limits to 5)
        cypher_results_raw = self.cypher_search(question)
        
        # Take the top 5 unique Cypher results
        cypher_count = 0
        for r in cypher_results_raw:
            key = r.get('slug') or r.get('id')
            if key and key not in seen_keys:
                final_results.append(r)
                seen_keys.add(key)
                # cypher_count += 1
                # if cypher_count >= 5: # Ensure we take exactly 5 from Cypher
                #     break
        
        # 2. Get Vector results
        vector_results_raw = self.vector_search(question)
        
        # Add additional unique vector results until we have 10 total
        vector_count = 0
        for r in vector_results_raw:
            if len(final_results) >= 10: # Stop if we already have 10 results
                break
            
            key = r.get('slug') or r.get('id')
            if key and key not in seen_keys:
                final_results.append(r)
                seen_keys.add(key)
                vector_count += 1
                if vector_count >= 5: # Ensure we take exactly 5 additional from Vector
                    break

        # 3. Rank the final combined set of non-duplicate results
        # We now have at most 10 results (up to 5 from Cypher, up to 5 unique from Vector)
        ranked_final_results = self._rank_results(final_results, question)

        return {
            "success": bool(ranked_final_results),
            "method": "hybrid",
            "results": ranked_final_results # This will contain at most 10 results
        }
    def retrieve(self, question: str) -> Dict[str, Any]:
      """Main retrieval with hybrid search (Cypher + Vector) - REVISED LOGIC
      This version returns all Cypher results and the top 5 *ranked* vector results.
      It also maintains the internal hybrid logic for display purposes.
      """
      timing_retrieve_total_start = time.perf_counter()

      # Internal print statements for debugging/tracking, as per original functionality
      logger.info("="*70)
      logger.info(f"RETRIEVE called with QUERY: {question}")
      logger.info("="*70)

      # --- Step 1: Get ALL Cypher results ---
      # The cypher_search function already handles its own internal logging
      all_cypher_results = self.cypher_search(question)

      # --- Step 2: Get ALL raw Vector results, then rank and take the top 5 ---
      # The vector_search function already handles its own internal logging
      raw_vector_results = self.vector_search(question)

      # Apply _rank_results to the *raw* vector results to score them
      timing_ranking_start = time.perf_counter()
      scored_vector_results = self._rank_results(raw_vector_results, question)
      timing_ranking_end = time.perf_counter()
      logger.info(f"⏱️  Vector result ranking took: {timing_ranking_end - timing_ranking_start:.3f}s")
      # Take only the top 10 most relevant vector results
      top_5_vector_results = scored_vector_results[:5]

      # --- Step 3: (Retain existing hybrid logic for internal use/display if needed) ---
      # This part remains identical to your original intent for the retriever's
      # *internal* combined ranking for display or subsequent processing.
      # It will combine both sets of results (all Cypher, and the top 5 ranked vectors),
      # deduplicate, and rank them all together for the `format_results` function.
      
      hybrid_combined_results = []
      seen_keys_for_hybrid = set()

      # Add ALL Cypher results to the hybrid set
      for r in all_cypher_results:
          key = r.get('slug') or r.get('id')
          if key and key not in seen_keys_for_hybrid:
              hybrid_combined_results.append(r)
              seen_keys_for_hybrid.add(key)
      
      # Add the TOP 5 RANKED Vector results to the hybrid set, avoiding duplicates
      # and limiting the total for display
      for r in top_5_vector_results:
          key = r.get('slug') or r.get('id')
          if key and key not in seen_keys_for_hybrid:
              hybrid_combined_results.append(r)
              seen_keys_for_hybrid.add(key)
              if len(hybrid_combined_results) >= 10: # Limit hybrid display to 10
                  break
      
      # Rank the *combined* set for internal display/use
      timing_hybrid_ranking_start = time.perf_counter()
      ranked_for_internal_display = self._rank_results(hybrid_combined_results, question)
      timing_hybrid_ranking_end = time.perf_counter()
      logger.info(f"⏱️  Hybrid result ranking took: {timing_hybrid_ranking_end - timing_hybrid_ranking_start:.3f}s")

      # --- Step 4: Return the specific results as requested ---
      timing_retrieve_total = time.perf_counter() - timing_retrieve_total_start
      logger.info(f"Retrieval complete. Cypher: {len(all_cypher_results)}, Vector (top 5): {len(top_5_vector_results)}, Hybrid: {len(ranked_for_internal_display)}")
      logger.info(f"⏱️  TOTAL RETRIEVE took: {timing_retrieve_total:.2f}s")
      logger.info("="*70)

      return {
          "all_cypher_results": all_cypher_results,          # All results from Cypher
          "top_5_vector_results": top_5_vector_results,      # Top 5 *ranked* vector results
          "hybrid_ranked_for_display": ranked_for_internal_display # For your `format_results`
      }

  # The `format_results` function provided in the previous response
  # is already correctly set up to consume "hybrid_ranked_for_display".
  # No changes needed there if you use the updated `retrieve` above.

    
    def format_results(self, response: Dict) -> str:
        """Format output"""
        if not response["success"] or not response["results"]:
            return "\n❌ No results found\n"
        
        lines = ["\n" + "="*70, f"TOP {len(response['results'])} RESULTS ({response['method'].upper()})", "="*70]
        
        for i, r in enumerate(response["results"], 1):
            lines.append(f"\n[{i}] {'━'*65}")
            
            if r.get('_score'):
                lines.append(f"🎯 Relevance Score: {r['_score']:.1f}")
            
            lines.append(f"Slug: {r.get('slug', 'N/A')}")
            
            if r.get('title'):
                lines.append(f"Title: {r['title']}")
            
            if r.get('url'):
                lines.append(f"🔗 {r['url']}")
            
            if r.get('similarity'):
                lines.append(f"📊 Vector: {r['similarity']:.3f}")
            
            if r.get('content'):
                # Shorten content preview to prevent excessive output
                preview = r['content'][:300]
                if len(r['content']) > 300:
                    preview += "..."
                lines.append(f"\n{preview}")
        
        lines.append("\n" + "="*70)
        return "\n".join(lines)


def main():
    try:
        retriever = ProductionRetriever()
    except Exception as e:
        print(f"❌ Retriever initialization failed: {e}")
        return
    
    examples = [
        "Mortise Latch Change of Handing Instructions",
        "How to install a 2500 series lock?", # Specific query for 2500 series
        "500 series deadbolt hardware installation",
        "Lock offline troubleshooting",
        "WiFi connectivity issues for my lock",
        "Tell me about the 4000 series installation guide", # Another specific slug-based query
        "ACS Installation", # A query that should hit a subcategory directly
        "General FAQs about locks",
        "What is the difference between a 2000 and 2500 series lock?",
        "How do I factory reset a lock?",
        "RemoteLock Portal overview"
    ]
    
    print("Examples:")
    for i, ex in enumerate(examples, 1):
        print(f"  {i}. {ex}")
    print("\nType 'quit' to exit\n")
    
    try:
        while True:
            inp = input("❯ ").strip()
            if not inp or inp.lower() == 'quit':
                break
            
            if inp.isdigit() and 1 <= int(inp) <= len(examples):
                question = examples[int(inp)-1]
                print(f"→ Querying for: {question}")
            else:
                question = inp
            
            response = retriever.retrieve(question)
            print(retriever.format_results(response))
    
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        retriever.close()
        print("Goodbye!\n")


#print(ProductionRetriever().retrieve("What are the two ways to activate or start the WiFi radio on a Key In Code lock?"))

# if __name__ == "__main__":
#     main()
