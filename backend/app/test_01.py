import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("models/gemini-2.5-flash")

response = model.generate_content("Say hello in 3 different ways.")
print(response.text)





# from neo4j import GraphDatabase

# driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "123456789"))

# with driver.session() as session:
#     result = session.run("RETURN 'Hello Neo4j' AS msg")
#     for record in result:
#         print(record["msg"])
