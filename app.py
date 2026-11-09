import os
import time
import io
import json
import re
import concurrent.futures
import pandas as pd
import requests
import streamlit as st
from PIL import Image
from google import genai
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

st.set_page_config(
    page_title="Enterprise Data Engineering Studio",
    page_icon="⚡",
    layout="wide"
)

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={'timeout': 60000}
)

SYSTEM_PROMPT = """
You are an elite Principal Data Engineering & Distributed Systems Architect. Write clean, production-ready code (Python ETL scripts with explicit server paths, ports, and multi-table targets, PySpark, Java, Scala, SQL Server T-SQL, MongoDB Aggregation/PyMongo, MySQL, PostgreSQL, Oracle, Snowflake, Cassandra CQL, Kubernetes K8s YAML, AWS EKS Helm, data lineage DAGs, FinOps optimization reports, traceback autopsies, unit tests) based on the requirement and connection parameters. Output ONLY clean, production-grade output with brief practical comments.
"""

def build_connection_uri(db_type, host, port, db_name, user, password):
    if db_type == "SQL Server":
        return f"mssql+pyodbc://{user}:{password}@{host}:{port}/{db_name}?driver=ODBC+Driver+17+for+SQL+Server"
    elif db_type == "PostgreSQL":
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"
    elif db_type == "MySQL":
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"
    elif db_type == "Oracle":
        return f"oracle+cx_oracle://{user}:{password}@{host}:{port}/{db_name}"
    elif db_type == "Snowflake":
        return f"snowflake://{user}:{password}@{host}/{db_name}"
    return None

def extract_and_transform_data(source_config, targets):
    processed_dfs = {}
    try:
        if source_config["type"] in ["SQL Server", "PostgreSQL", "MySQL", "Oracle", "Snowflake"]:
            uri = build_connection_uri(
                source_config["type"], source_config["host"], source_config["port"], 
                source_config["db_name"], source_config["user"], source_config["password"]
            )
            engine = create_engine(uri)
            for table in targets.get("tables", []):
                df = pd.read_sql(f"SELECT * FROM {table}", con=engine)
                for col in df.select_dtypes(include=['object']).columns:
                    df[col] = df[col].astype(str).str.strip()
                num_cols = df.select_dtypes(include=['number']).columns
                df[num_cols] = df[num_cols].fillna(0)
                processed_dfs[table] = df
        elif source_config["type"] == "REST API":
            for api_url in targets.get("apis", []):
                response = requests.get(api_url, timeout=30)
                if response.status_code == 200:
                    df = pd.DataFrame(response.json())
                    df.columns = [c.lower().strip() for c in df.columns]
                    processed_dfs[api_url] = df
    except Exception as e:
        st.error(f"ETL Connection & Extraction Error: {e}")
    return processed_dfs

def generate_code(fw, config_context, requirement, uploaded_file):
    contents_list = []
    prompt = f"Target Module/Framework: {fw}\nConnection & Schema Parameters:\n{config_context}\nUser Requirement: {requirement}"
    contents_list.append(prompt)
    if uploaded_file:
        try:
            img = Image.open(uploaded_file)
            contents_list.append(img)
        except Exception:
            pass

    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=contents_list,
                config={'system_instruction': SYSTEM_PROMPT, 'temperature': 0.1}
            )
            return fw, response.text
        except Exception as e:
            if attempt == 1:
                return fw, f"# Error generating {fw}: {e}"
            time.sleep(1)

# --- SIMPLE APP HEADER ---
st.title("⚡ Enterprise Data Engineering Studio")
st.markdown("Unified Code Generator, Multi-Source Connector & ETL Pipeline Orchestrator")
st.markdown("---")

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("🔌 Server & Connection Config")
    db_type = st.selectbox("Source Database / Engine", ["SQL Server", "PostgreSQL", "MySQL", "Oracle", "Snowflake", "REST API"])
    host_path = st.text_input("Network Host / Server Path", value="localhost" if db_type != "REST API" else "https://api.example.com/v1")
    port_num = st.text_input("Port Number", value="1433" if db_type == "SQL Server" else ("5432" if db_type == "PostgreSQL" else "3306"))
    db_name = st.text_input("Database Name / Service", value="enterprise_dw")
    db_user = st.text_input("Username", value="sa")
    db_pass = st.text_input("Password", type="password", value="")
    target_items = st.text_input("Target Tables / API Endpoints (comma-separated)", value="dbo.dim_customers, dbo.fact_sales")

    st.markdown("---")
    st.header("⚙️ Generation Modules")
    frameworks = st.multiselect(
        "Select Frameworks", 
        [
            "Python Scripting & CLI Automation",
            "PySpark API Ingestion", 
            "Scala Data Pipeline (Spark)",
            "Java Data Pipeline (Spark/Flink)",
            "SQL Server (T-SQL, Stored Procedures, SSIS)",
            "MongoDB (PyMongo & Aggregation Pipelines)",
            "MySQL SQL & Stored Procedures",
            "PostgreSQL & PL/pgSQL",
            "Oracle PL/SQL & Packages",
            "Snowflake SQL & Snowpark",
            "Cassandra CQL & Data Modeling",
            "Kubernetes (K8s) Deployment Manifests",
            "AWS EKS Cluster Config & Helm Charts",
            "Batch Script (.bat / Automation)", 
            "Azure Data Factory (ADF) Logic", 
            "Data Quality & QA Assertions",
            "Automated Unit Tests (pytest)",
            "Data Lineage & DAG Schema Visualizer",
            "Spark & Warehouse FinOps Cost Optimizer",
            "Automated Log & Traceback Autopsy"
        ],
        default=[
            "Python Scripting & CLI Automation",
            "SQL Server (T-SQL, Stored Procedures, SSIS)",
            "PySpark API Ingestion", 
            "Snowflake SQL & Snowpark",
            "Kubernetes (K8s) Deployment Manifests"
        ]
    )

# --- MAIN WORKSPACE ---
st.subheader("📝 Describe Your Data Engineering Task")
requirement = st.text_area(
    "Requirement Prompt",
    value="Extract multiple tables from the configured server host/port, apply data cleaning transformations, and ingest into Snowflake deployed on Kubernetes.",
    height=120,
    label_visibility="collapsed"
)

uploaded_file = st.file_uploader("📎 Attach Architecture Diagram or Error Traceback (Optional)", type=["png", "jpg", "jpeg", "pdf"], key="main_uploader")

col_b1, col_b2 = st.columns(2)
with col_b1:
    run_gen = st.button("🚀 Generate Enterprise Code & Infrastructure", type="primary", use_container_width=True)
with col_b2:
    run_etl = st.button("▶️ Run Live Extract & Transform (ETL)", use_container_width=True)

config_context = f"""
- Source Engine: {db_type}
- Network Host / Path: {host_path}
- Port: {port_num}
- Database Name: {db_name}
- Username: {db_user}
- Target Tables / Endpoints: {target_items}
"""

if "generated_results" not in st.session_state:
    st.session_state.generated_results = {}

if run_gen:
    if not requirement.strip() and not uploaded_file:
        st.warning("Please provide a requirement or upload a file.")
    else:
        st.session_state.generated_results = {}
        with st.spinner("Generating production-grade code across selected modules..."):
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                futures = {executor.submit(generate_code, fw, config_context, requirement, uploaded_file): fw for fw in frameworks}
                for future in concurrent.futures.as_completed(futures):
                    fw, code = future.result()
                    st.session_state.generated_results[fw] = code

if run_etl:
    source_config = {"type": db_type, "host": host_path, "port": port_num, "db_name": db_name, "user": db_user, "password": db_pass}
    targets = {"tables": [t.strip() for t in target_items.split(",") if t.strip()]} if db_type != "REST API" else {"apis": [a.strip() for a in target_items.split(",") if a.strip()]}
    
    with st.spinner("Connecting to server network path and processing live ETL pipeline..."):
        extracted_dfs = extract_and_transform_data(source_config, targets)
        if extracted_dfs:
            st.success(f"Successfully processed {len(extracted_dfs)} data targets!")
            for name, df in extracted_dfs.items():
                with st.expander(f"📦 Dataset: {name} ({len(df)} rows)", expanded=True):
                    st.dataframe(df.head(10), use_container_width=True)
        else:
            st.warning("No data retrieved. Verify connection parameters, network paths, and table permissions.")

if st.session_state.generated_results:
    st.markdown("---")
    st.subheader("📂 Generated Code Workspace")
    for fw in frameworks:
        if fw in st.session_state.generated_results:
            with st.expander(f"⚡ {fw}", expanded=True):
                code_text = st.session_state.generated_results[fw]
                if "Java" in fw: lang = "java"
                elif "Scala" in fw: lang = "scala"
                elif "Kubernetes" in fw or "EKS" in fw or "YAML" in fw: lang = "yaml"
                elif any(db in fw for db in ["SQL", "Postgres", "Oracle", "MySQL", "Cassandra", "Snowflake"]): lang = "sql"
                elif "Batch" in fw: lang = "batch"
                elif any(x in fw for x in ["DAG", "FinOps", "Autopsy"]): lang = "markdown"
                else: lang = "python"
                st.code(code_text, language=lang)