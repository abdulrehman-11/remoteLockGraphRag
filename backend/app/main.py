# customer_support_agent.py
import os
import operator
import logging
import sys
from datetime import datetime
from typing import Annotated, List, Tuple, Union, Dict, Any, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode #ToolExecutor
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, FunctionMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

# Import your ProductionRetriever and SITEMAP_STRUCTURE from the retriever file
# Use a package-relative import so this module works when run as 'app.main'
# (uvicorn imports the module as a package: e.g. `uvicorn app.main:app`).
from .query_with_llm_json import ProductionRetriever

load_dotenv()

# --- Logging Configuration ---
# Configure logging with fallback for environments with read-only filesystems (like Render)
handlers = [logging.StreamHandler(sys.stdout)]
try:
    # Try to create file handler in /tmp (writable on Render)
    handlers.append(logging.FileHandler('/tmp/app_logs.log'))
except Exception as e:
    print(f"Warning: Could not create log file, using stdout only: {e}")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

# CORS configuration for browser-based frontends (e.g., Vercel)
ALLOWED_ORIGINS_ENV = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",") if origin.strip()]

# Initialize the retriever instance once when the FastAPI app starts
# This ensures database connections are established on startup
retriever_instance: ProductionRetriever = None
try:
    logger.info("Initializing ProductionRetriever...")
    retriever_instance = ProductionRetriever()
    logger.info("ProductionRetriever initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize ProductionRetriever: {e}", exc_info=True)
    # The application can still start, but the tool calls will return an error

SITEMAP_STRUCTURE = {
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

# --- Tool Definition ---
# Wrap the retriever's functionality as a LangChain tool
@tool
def retrieve_documentation(query: str) -> Dict[str, Any]:
    """
    Retrieves documentation from the RemoteLock knowledge base using a hybrid search approach.
    It performs both Cypher graph search and vector similarity search.
    Returns a dictionary containing:
    - 'all_cypher_results': All raw results from the Cypher query.
    - 'top_5_vector_results': The top 5 most relevant results from the vector search, after ranking.
    - 'hybrid_ranked_for_display': A combined and ranked list of results suitable for internal display.
    """
    logger.info(f"retrieve_documentation tool called with query: {query}")

    if retriever_instance is None:
        logger.error("Retriever instance is None, cannot perform retrieval")
        return {"error": "Retriever was not initialized due to an earlier error. Cannot perform retrieval.", "query": query}

    try:
        # The retriever's retrieve method already returns the desired structure
        result = retriever_instance.retrieve(query)
        logger.info(f"Retrieval successful. Cypher results: {len(result.get('all_cypher_results', []))}, Vector results: {len(result.get('top_5_vector_results', []))}")
        return result
    except Exception as e:
        logger.error(f"Error during retrieval: {e}", exc_info=True)
        return {"error": f"Retrieval failed: {str(e)}", "query": query}

# Tools the LLM can use
tools = [retrieve_documentation]

# --- LangGraph State ---
# Using TypedDict for state, as it's more idiomatic for LangGraph mutable state updates
class GraphState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    sitemap: str # Sitemap accessible within the state
    # We don't strictly need 'tool_called' or 'retrieval_output' in the state
    # if the LLM's role is simply to process the `FunctionMessage` after tool execution.
    # LangGraph's ToolNode automatically adds the FunctionMessage to `messages`.

# --- LangGraph Nodes ---
def call_llm(state: GraphState) -> GraphState:
    """Invokes the LLM to generate a response or call a tool."""
    logger.info("call_llm node invoked")
    messages = state["messages"]
    sitemap_context = state["sitemap"]
    logger.debug(f"Processing {len(messages)} messages")

    # Construct the system prompt with sitemap context.
    # This prompt is *crucial* for guiding the LLM's behavior and tool-calling decisions.
    # It tells the LLM to use the sitemap to understand context and when to call the tool.
    # system_instruction = (
    #     "You are a helpful and knowledgeable RemoteLock customer support agent. "
    #     "Your goal is to assist users by providing accurate information from the RemoteLock knowledge base. "
    #     "You have access to a tool named `retrieve_documentation` that can search for relevant articles. "
    #     "Use the provided `Sitemap Structure` to understand the available documentation topics and hierarchy. "
    #     "This helps you determine if a query is related to an existing document or category. "
    #     "Prioritize using the `retrieve_documentation` tool when the user's question clearly asks for information "
    #     "that would be found in a support article, installation guide, troubleshooting step, or product information. "
    #     "Examples of when to use the tool: 'How do I install...', 'Troubleshoot my lock...', 'What is a 500 series...', "
    #     "'Information about the ACS integration...', 'Tell me about the Kwikset Halo...', 'Where can I find user manuals?'.\n\n"
    #     "If you use the `retrieve_documentation` tool:\n"
    #     "1. Examine the `all_cypher_results` for precise, fact-based answers or direct article links.\n"
    #     "2. Examine the `top_5_vector_results` for highly relevant articles based on semantic similarity.\n"
    #     "3. Prioritize information from `all_cypher_results` if it contains exact matches or direct answers.\n"
    #     "4. Synthesize a concise and helpful response. Always include a link (URL) to the most relevant article if one is found.\n"
    #     "5. If multiple articles are relevant, briefly summarize the top one or two and offer more if needed.\n"
    #     "6. If no relevant information is found by the tool, apologize and suggest alternative support channels (e.g., 'Please contact our live support for further assistance.').\n"
    #     "7. DO NOT generate made-up information. Stick strictly to the retrieved content.\n\n"
    #     "Sitemap Structure (for contextual understanding, DO NOT directly output this to the user unless specifically asked):\n"
    #     f"{sitemap_context}\n"
    #     "--------------------\n"
    #     "Begin conversation:"
    # )
#     system_instruction = (
#     "You are a helpful and knowledgeable RemoteLock customer support agent. "
#     "Your primary goal is to assist users by providing accurate, precise, and professional information "
#     "from the RemoteLock knowledge base. You have access to a tool named `retrieve_documentation` "
#     "that can search for relevant articles. "
#     "Use the provided `Sitemap Structure` to understand the available documentation topics and hierarchy. "
#     "This helps you determine if a query is related to an existing document or category and guides your search. "
#     "Prioritize using the `retrieve_documentation` tool when the user's question clearly asks for information "
#     "that would be found in a support article, installation guide, troubleshooting step, or product information. "
#     "Examples of when to use the tool: 'How do I install...', 'Troubleshoot my lock...', 'What is a 500 series...', "
#     "'Information about the ACS integration...', 'Tell me about the Kwikset Halo...', 'Where can I find user manuals?'.\n\n"
#     "When you receive a response from the `retrieve_documentation` tool, follow these steps to reason and generate your output:\n"
#     "1.  **Thoroughly Review All Retrieved Content:** Examine both `all_cypher_results` and `top_5_vector_results`. "
#     "    Read through the full content of the retrieved documents, not just their titles or snippets, to understand the context fully. "
#     "    Pay close attention to the `cypher` results first, as they often provide more direct and structured information.\n"
#     "2.  **Prioritize Cypher Results for Direct Answers:** If `all_cypher_results` contain precise, fact-based answers, "
#     "    direct article links, or highly relevant sections that directly address the user's question, prioritize this information.\n"
#     "3.  **Integrate Vector Results for Semantic Relevance:** If `cypher` results are less direct or if `vector` results "
#     "    offer semantically similar articles that complement or further explain the user's query, integrate this information. "
#     "    Look for details in the vector results that directly answer the question, even if the cypher results were broad.\n"
#     "4.  **Reason and Extract Key Information:** Based on your comprehensive review, extract the most relevant and critical information "
#     "    that directly answers the user's question. Do not just summarize; reason about *what* the user is asking "
#     "    and *how* the retrieved content provides that answer. Focus on being simple and precise.\n"
#     "5.  **Formulate a Concise and Professional Response:** Synthesize the extracted information into a clear, professional, "
#     "    and easy-to-understand response. Avoid jargon where possible. If the retrieved content has a direct answer, "
#     "    provide it immediately.\n"
#     "6.  **Always Include the Most Relevant Link(s):** Crucially, **always include the URL(s) to the most relevant article(s)** "
#     "    from the retrieved content. If an article from `cypher` or `vector` results provides the core answer, "
#     "    its link must be provided. If multiple articles are highly relevant, you may briefly mention one or two "
#     "    and offer the user to explore others if needed. **Ensure the link is directly from the retrieved data.**\n"
#     "7.  **Handle Missing Information Gracefully:** If, after a thorough review of both `cypher` and `vector` results, "
#     "    no sufficiently relevant information is found to directly answer the user's question, apologize gracefully "
#     "    and suggest alternative support channels (e.g., 'I couldn't find a direct answer to your question in our knowledge base. "
#     "    Please contact our live support for further assistance, or you can check our main support page here: [link to main support page if available from sitemap context, otherwise omit if not found in retrieved data].'). "
#     "    **DO NOT default to 'contact support' if relevant information is present in the retrieved content.**\n"
#     "8.  **Strictly Adhere to Retrieved Content:** DO NOT generate made-up information or infer details not present "
#     "    in the retrieved documentation. Your response must be strictly based on the provided content.\n\n"
#     "Sitemap Structure (for contextual understanding, DO NOT directly output this to the user unless specifically asked):\n"
#     f"{sitemap_context}\n"
#     "--------------------\n"
#     "Begin conversation:"
# )

    system_instruction = (
    "You are a helpful and knowledgeable RemoteLock customer support agent. "
    "Your primary goal is to assist users by providing accurate, precise, and professional information "
    "from the RemoteLock knowledge base. You have access to a tool named `retrieve_documentation` "
    "that can search for relevant articles. "
    "Use the provided `Sitemap Structure` to understand the available documentation topics and hierarchy. "
    "This helps you determine if a query is related to an existing document or category and guides your search. "
    "Prioritize using the `retrieve_documentation` tool when the user's question clearly asks for information "
    "that would be found in a support article, installation guide, troubleshooting step, or product information. "
    "Examples of when to use the tool: 'How do I install...', 'Troubleshoot my lock...', 'What is a 500 series...', "
    "'Information about the ACS integration...', 'Tell me about the Kwikset Halo...', 'Where can I find user manuals?'.\n\n"
    "When you receive a response from the `retrieve_documentation` tool, follow these steps to reason and generate your output:\n"
    "1.  **Thoroughly Review All Retrieved Content:** Examine both `all_cypher_results` and `top_5_vector_results`. "
    "    Read through the full content of the retrieved documents, not just their titles or snippets, to understand the context fully. "
    "    Pay close attention to the `cypher` results first, as they often provide more direct and structured information.\n"
    "2.  **Prioritize Cypher Results for Direct Answers & Direct Links:** If `all_cypher_results` contain precise, fact-based answers, "
    "    or highly relevant sections that directly address the user's question, prioritize this information. "
    "    **Special Case for Direct Redirects:** If a `cypher` result has exceptionally high similarity to the user's prompt "
    "    and its content primarily consists of a link or a directive to 'Click here to be directed through troubleshooting' (or similar), "
    "    **immediately provide that specific internal link** as the primary answer, explaining that it will direct them to the detailed steps. "
    "    For example, if the content is 'Click here to be directed through troubleshooting 👇' and it's from a highly relevant page, "
    "    directly output: 'It looks like the best resource for that is a dedicated troubleshooting guide. Please click here: [URL from page_content]'.\n"
    "3.  **Integrate Vector Results for Semantic Relevance:** If `cypher` results are less direct or if `vector` results "
    "    offer semantically similar articles that complement or further explain the user's query, integrate this information. "
    "    Look for details in the vector results that directly answer the question, even if the cypher results were broad.\n"
    "4.  **Reason and Extract Key Information:** Based on your comprehensive review, extract the most relevant and critical information "
    "    that directly answers the user's question. Do not just summarize; reason about *what* the user is asking "
    "    and *how* the retrieved content provides that answer. Focus on being simple and precise.\n"
    "5.  **Formulate a Concise and Professional Response:** Synthesize the extracted information into a clear, professional, "
    "    and easy-to-understand response. Avoid jargon where possible. If the retrieved content has a direct answer, "
    "    provide it immediately.\n"
    "6.  **Always Include the Most Relevant Link(s):** Crucially, **always include the URL(s) to the most relevant article(s)** "
    "    from the retrieved content. If an article from `cypher` or `vector` results provides the core answer, "
    "    its link must be provided. If multiple articles are highly relevant, you may briefly mention one or two "
    "    and offer the user to explore others if needed. **Ensure the link is directly from the retrieved data's 'link' field or the internal link within the page_content if it's a redirect.**\n"
    "7.  **Handle Missing Information Gracefully:** If, after a thorough review of both `cypher` and `vector` results, "
    "    no sufficiently relevant information is found to directly answer the user's question, apologize gracefully "
    "    and suggest alternative support channels (e.g., 'I couldn't find a direct answer to your question in our knowledge base. "
    "    Please contact our live support for further assistance, or you can check our main support page here: [link to main support page if available from sitemap context, otherwise omit if not found in retrieved data].'). "
    "    **DO NOT default to 'contact support' if relevant information is present in the retrieved content.**\n"
    "8.  **Strictly Adhere to Retrieved Content:** DO NOT generate made-up information or infer details not present "
    "    in the retrieved documentation. Your response must be strictly based on the provided content.\n\n"

    "Begin conversation:"
)





    # Ensure system prompt is only added once at the beginning of the conversation.
    # If messages are reset per API call (as in this example), it's fine to re-add.
    # For a persistent session, you'd check if the first message is already a system message.
    
    # Create the full message history to send to the LLM, including the system prompt.
    # Gemini models often handle a system-like prompt best as the first HumanMessage or AIMessage.
    # Using AIMessage for system role is a common pattern for Gemini within LangChain.
    llm_messages = [AIMessage(content=system_instruction, role='system')] + messages

    logger.info("Invoking LLM with tools...")
    try:
        response = llm_with_tools.invoke(llm_messages)
        logger.info(f"LLM response received. Tool calls: {len(response.tool_calls) if hasattr(response, 'tool_calls') and response.tool_calls else 0}")

        # LangGraph will use operator.add to append this response to the state's messages list.
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"Error invoking LLM: {e}", exc_info=True)
        raise


# The ToolNode prebuilt class automatically handles tool execution and adds results to messages.
# We don't need a custom `call_tool_node` function if we just use `ToolNode`.

# --- LLM Setup ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", # Using flash for faster responses, can switch to pro if needed
    temperature=0.2, # Slightly less creative for support, more factual
    google_api_key=GEMINI_API_KEY,
    convert_system_message_to_human=True # Important for LangChain's Gemini integration, treats system as human internally
)
llm_with_tools = llm.bind_tools(tools)

# --- LangGraph Agent Construction ---
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("llm", call_llm)
workflow.add_node("tool", ToolNode(tools)) # Using the prebuilt ToolNode

# Set entry point
workflow.set_entry_point("llm")

# Define edges
# If the LLM's last message contains tool_calls, transition to the 'tool' node.
# Otherwise, the conversation is effectively over for this turn (END).
workflow.add_conditional_edges(
    "llm",
    lambda state: "tool" if state["messages"][-1].tool_calls else END,
    {"tool": "tool", END: END}
)

# After the tool is executed, transition back to the LLM to process the tool's output.
workflow.add_edge("tool", "llm")

# Compile the graph
app_graph = workflow.compile()

# --- FastAPI Application ---
app = FastAPI(
    title="RemoteLock Customer Support Agent",
    description="An AI-powered customer support agent for RemoteLock documentation, built with LangGraph and FastAPI.",
    version="1.0.0",
)

# Enable CORS so a deployed frontend can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],  # Prefer explicit origins via ALLOWED_ORIGINS env
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint for basic health check"""
    return {"message": "RemoteLock AI Assistant API is running", "status": "ok"}

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and deployment verification"""
    return {
        "status": "healthy",
        "retriever_initialized": retriever_instance is not None,
        "gemini_api_configured": GEMINI_API_KEY is not None
    }

# Model for incoming chat messages
class ChatMessage(BaseModel):
    message: str

@app.post("/chat/")
async def chat_endpoint(chat_message: ChatMessage) -> Dict[str, str]:
    """
    Handle incoming chat messages and generate a response using the LangGraph agent.
    """
    logger.info(f"Received chat request: {chat_message.message[:100]}...")
    user_message = HumanMessage(content=chat_message.message)
    
    # For a persistent chat session across multiple /chat calls:
    # You would need a mechanism to store and retrieve the `messages` history
    # associated with a user's session (e.g., a dictionary, database, or session management).
    # For this example, we'll keep it simple: the conversation history exists *only* within
    # a single `app_graph.invoke` call. This means each `/chat` call is a new "turn"
    # that starts with the user's message, runs the graph, and responds.
    # If you want multi-turn memory, you'll need to pass `final_state["messages"]`
    # from the previous turn into the `initial_state` of the next.

    initial_state_for_this_turn = {
        "messages": [user_message],
        "sitemap": SITEMAP_STRUCTURE, # Always provide sitemap to the graph state
    }

    try:
        # Run the graph. LangGraph will manage the `messages` state list internally
        # by appending LLM responses and FunctionMessages from tool calls.
        logger.info("Invoking LangGraph agent...")
        final_state = app_graph.invoke(initial_state_for_this_turn)
        logger.info("LangGraph execution completed")

        # The last message in the final state should be the agent's ultimate response
        agent_final_response = final_state["messages"][-1]

        # Ensure we're getting the content correctly, even if it's a tool call object that ended the graph
        response_content = agent_final_response.content if isinstance(agent_final_response, (AIMessage, HumanMessage)) else str(agent_final_response)

        logger.info(f"Response generated successfully. Length: {len(response_content)} chars")
        return {"response": response_content}

    except Exception as e:
        logger.error(f"Error during chat processing: {e}", exc_info=True)
        return {"response": "I'm sorry, I encountered an error. Please try again or contact support."}
