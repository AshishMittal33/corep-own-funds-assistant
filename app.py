import streamlit as st
import pandas as pd
import json
from datetime import datetime
import time
from corep_engine import COREPEngine

# Page configuration
st.set_page_config(
    page_title="PRA COREP Reporting Assistant",
    page_icon="🏛️",
    layout="wide"
)

# Custom CSS without external dependencies
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.4rem;
        color: #374151;
        margin-top: 1rem;
        font-weight: bold;
    }
    .success-box {
        background-color: #D1FAE5;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #10B981;
    }
    .warning-box {
        background-color: #FEF3C7;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #F59E0B;
    }
    .error-box {
        background-color: #FEE2E2;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #EF4444;
    }
    .info-box {
        background-color: #E0F2FE;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #0EA5E9;
    }
    .stButton button {
        width: 100%;
    }
    .stTextArea textarea {
        font-family: monospace;
    }
    .highlight {
        background-color: #F3F4F6;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'engine' not in st.session_state:
    st.session_state.engine = None
if 'results' not in st.session_state:
    st.session_state.results = None
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'current_query' not in st.session_state:
    st.session_state.current_query = ""

# Initialize engine
@st.cache_resource
def init_engine():
    try:
        return COREPEngine()
    except Exception as e:
        st.error(f"Failed to initialize: {str(e)}")
        return None

def main():
    # Header
    st.markdown('<h1 class="main-header">🏛️ PRA COREP Regulatory Reporting Assistant</h1>', 
                unsafe_allow_html=True)
    st.markdown("**Prototype v1.0** - AI-powered assistant for COREP regulatory reporting")
    
    # Sidebar
    with st.sidebar:
        st.title("Navigation")
        
        menu = st.radio(
            "Select Mode:",
            ["📝 Generate Report", "📊 Template Info", "📚 View Rules", "🔄 History"]
        )
        
        st.divider()
        
        st.markdown("### Quick Examples")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Complete Data"):
                st.session_state.current_query = """Bank has:
- Ordinary shares: £200,000,000
- Share premium: £80,000,000
- Retained earnings: £350,000,000
- Intangible assets: £60,000,000
- Other comprehensive income: £30,000,000
- Risk Weighted Assets: £8,000,000,000"""
        
        with col2:
            if st.button("Missing Data"):
                st.session_state.current_query = "Bank has £100M shares and £50M earnings only."
        
        if st.button("Rules Question"):
            st.session_state.current_query = "What fields are required for CET1 reporting?"
        
        st.divider()
        
        st.markdown("### About")
        st.info("""
        **Scope**: COREP C 01.00 (Own Funds - CET1)
        
        **Regulations**: CRR Articles 26 & 36
        
        **Template**: Own Funds reporting
        """)
    
    # Main content
    if menu == "📝 Generate Report":
        show_report_generator()
    elif menu == "📊 Template Info":
        show_template_info()
    elif menu == "📚 View Rules":
        show_rules()
    elif menu == "🔄 History":
        show_history()

def show_report_generator():
    st.markdown('<h2 class="sub-header">📝 Generate COREP Report</h2>', unsafe_allow_html=True)
    
    # Input section
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### Enter Scenario")
        
        # Text area with current query
        user_input = st.text_area(
            "Describe your scenario or ask a question:",
            value=st.session_state.current_query,
            height=180,
            placeholder="""Example: Bank has £150M ordinary shares, £75M share premium, £300M retained earnings, £45M intangible assets...""",
            key="scenario_input"
        )
        
        # Clear current query after using it
        if st.session_state.current_query:
            st.session_state.current_query = ""
    
    with col2:
        st.markdown("### Options")
        
        st.checkbox("Run validation", value=True, key="run_validation")
        st.checkbox("Show audit trail", value=True, key="show_audit")
        st.checkbox("Save to file", value=True, key="save_file")
        
        st.divider()
        
        if st.button("🚀 Generate Report", type="primary", use_container_width=True):
            if user_input.strip():
                process_report(user_input)
            else:
                st.warning("Please enter a scenario first.")
    
    # Display results if available
    if st.session_state.results:
        display_results()

def process_report(user_input):
    """Process the user query"""
    
    # Initialize progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Initialize engine
    if st.session_state.engine is None:
        status_text.text("Initializing engine...")
        st.session_state.engine = init_engine()
    
    if st.session_state.engine is None:
        st.error("Failed to initialize engine. Check your API key and files.")
        return
    
    try:
        # Step 1: Processing
        status_text.text("Processing your request...")
        progress_bar.progress(30)
        
        # Process query
        result = st.session_state.engine.process_query(user_input)
        
        if result.get("error"):
            st.error(f"Error: {result['error']}")
            return
        
        # Step 2: Validation
        status_text.text("Validating results...")
        progress_bar.progress(70)
        
        # Step 3: Complete
        status_text.text("Generating report...")
        progress_bar.progress(100)
        
        # Store results
        st.session_state.results = result
        
        # Add to history
        st.session_state.query_history.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "query": user_input[:80] + "..." if len(user_input) > 80 else user_input,
            "status": "✅" if result["validation"]["is_valid"] else "⚠️"
        })
        
        # Clear status
        time.sleep(0.5)
        status_text.empty()
        progress_bar.empty()
        
        st.success("Report generated successfully!")
        
    except Exception as e:
        st.error(f"Error processing request: {str(e)}")
        status_text.empty()
        progress_bar.empty()

def display_results():
    """Display the results"""
    
    if not st.session_state.results:
        return
    
    result = st.session_state.results
    template_data = result["template_data"]
    validation = result["validation"]
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Template", "🔍 Validation", "📑 Audit", "📋 Summary"])
    
    with tab1:
        display_template(template_data)
    
    with tab2:
        display_validation(validation, template_data)
    
    with tab3:
        if "audit_trail" in template_data:
            display_audit(template_data["audit_trail"])
        else:
            st.info("No audit trail available.")
    
    with tab4:
        display_summary(result)
    
    # Export options
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Save as JSON"):
            save_json(result)
    
    with col2:
        if st.button("🔄 New Report"):
            st.session_state.results = None
            st.rerun()

def display_template(template_data):
    """Display COREP template"""
    
    st.markdown("### COREP Template C 01.00 - Own Funds (CET1)")
    
    # Extract data
    data = template_data.get("data", {})
    
    # Create table
    rows = []
    for code in ["010", "020", "030", "040", "070", "100"]:
        if code in data:
            field_info = data[code]
            value = field_info.get("value", "0")
            desc = field_info.get("description", "")
            
            # Format value
            try:
                val_int = int(value) if value else 0
                if field_info.get("is_deduction", False):
                    formatted = f"£({abs(val_int):,})"
                else:
                    formatted = f"£{val_int:,}"
            except:
                formatted = value
            
            rows.append({
                "Row": code,
                "Description": desc,
                "Amount": formatted,
                "Type": "Deduction" if field_info.get("is_deduction", False) else "Component"
            })
    
    # Display as dataframe
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            column_config={
                "Row": st.column_config.TextColumn(width="small"),
                "Description": st.column_config.TextColumn(width="medium"),
                "Amount": st.column_config.TextColumn(width="medium"),
                "Type": st.column_config.TextColumn(width="small")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning("No template data available.")
    
    # Show calculations
    if "calculations" in template_data:
        with st.expander("View Calculations"):
            for calc_name, calc_formula in template_data["calculations"].items():
                st.code(calc_formula, language="text")

def display_validation(validation, template_data):
    """Display validation results"""
    
    errors = validation.get("errors", [])
    warnings = validation.get("warnings", [])
    
    # Errors
    if errors:
        st.markdown('<div class="error-box">', unsafe_allow_html=True)
        st.markdown("### ❌ Validation Errors")
        for error in errors:
            st.markdown(f"- {error}")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="success-box">', unsafe_allow_html=True)
        st.markdown("### ✅ No Validation Errors")
        st.markdown("All checks passed successfully.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Warnings
    if warnings:
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.markdown("### ⚠️ Validation Warnings")
        for warning in warnings:
            st.markdown(f"- {warning}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # LLM validation notes
    validation_notes = template_data.get("validation_notes", [])
    if validation_notes:
        st.markdown("### 📋 Additional Notes")
        for note in validation_notes:
            if isinstance(note, dict):
                note_type = note.get("type", "INFO")
                message = note.get("message", "")
                st.info(f"[{note_type}] {message}")
            else:
                st.info(str(note))

def display_audit(audit_trail):
    """Display audit trail"""
    
    if not audit_trail:
        st.info("No audit trail available.")
        return
    
    st.markdown("### 📑 Regulatory Audit Trail")
    
    for entry in audit_trail:
        if isinstance(entry, dict):
            field = entry.get('field', 'N/A')
            rule = entry.get('rule', 'No rule')
            justification = entry.get('justification', 'No justification')
            
            with st.expander(f"Field {field}"):
                st.markdown(f"**Rule:** `{rule}`")
                st.markdown(f"**Justification:** {justification}")
        else:
            # Handle string entries
            with st.expander(f"Audit Entry"):
                st.info(str(entry))

def display_summary(result):
    """Display summary"""
    
    template_data = result["template_data"]
    validation = result["validation"]
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fields = len(template_data.get("data", {}))
        st.metric("Fields Populated", fields)
    
    with col2:
        errors = len(validation.get("errors", []))
        st.metric("Errors", errors, delta_color="inverse")
    
    with col3:
        warnings = len(validation.get("warnings", []))
        st.metric("Warnings", warnings)
    
    # Summary info
    st.markdown("### Report Details")
    
    summary_info = f"""
    - **Template**: {template_data.get('template', 'N/A')}
    - **Reporting Date**: {template_data.get('reporting_date', 'N/A')}
    - **Currency**: {template_data.get('currency', 'N/A')}
    - **Generated**: {result.get('timestamp', 'N/A')}
    - **Query**: {result.get('user_query', 'N/A')[:100]}...
    """
    
    st.markdown(summary_info)

def save_json(result):
    """Save results to JSON"""
    
    filename = f"corep_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Prepare download data
    json_str = json.dumps(result, indent=2)
    
    st.download_button(
        label="📥 Download JSON File",
        data=json_str,
        file_name=filename,
        mime="application/json"
    )

def show_template_info():
    """Show template information"""
    
    st.markdown('<h2 class="sub-header">📊 COREP Template Information</h2>', unsafe_allow_html=True)
    
    try:
        # Load schema
        with open("schema_c0100.json", "r") as f:
            schema = json.load(f)
        
        st.markdown(f"**Template:** {schema.get('template_id', 'N/A')}")
        st.markdown(f"**Name:** {schema.get('template_name', 'N/A')}")
        st.markdown(f"**Version:** {schema.get('version', 'N/A')}")
        
        st.divider()
        
        # Display fields
        st.markdown("### CET1 Capital Fields")
        
        fields_data = []
        if 'sections' in schema:
            for section_name, section in schema['sections'].items():
                for field in section.get('fields', []):
                    fields_data.append({
                        "Code": field.get('code'),
                        "Name": field.get('name'),
                        "Required": "Yes" if field.get('required', False) else "No",
                        "Type": "Deduction" if field.get('is_deduction', False) else "Component",
                        "Rule": field.get('rule_reference', 'N/A')
                    })
        
        if fields_data:
            df = pd.DataFrame(fields_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("No field information available.")
    
    except FileNotFoundError:
        st.error("Template schema file not found.")
    except json.JSONDecodeError:
        st.error("Invalid JSON in schema file.")

def show_rules():
    """Show regulatory rules"""
    
    st.markdown('<h2 class="sub-header">📚 Regulatory Rules</h2>', unsafe_allow_html=True)
    
    try:
        with open("rules.txt", "r") as f:
            rules_content = f.read()
        
        # Display in expandable sections
        lines = rules_content.split('\n')
        current_section = ""
        section_content = []
        
        for line in lines:
            if line.startswith('## '):
                # Save previous section
                if current_section and section_content:
                    with st.expander(current_section):
                        st.markdown('\n'.join(section_content))
                
                # Start new section
                current_section = line[3:].strip()
                section_content = []
            elif line.startswith('### '):
                # Subsection
                if section_content:
                    section_content.append(f"**{line[4:]}**")
            else:
                section_content.append(line)
        
        # Save last section
        if current_section and section_content:
            with st.expander(current_section):
                st.markdown('\n'.join(section_content))
    
    except FileNotFoundError:
        st.error("Rules file not found.")

def show_history():
    """Show query history"""
    
    st.markdown('<h2 class="sub-header">🔄 Query History</h2>', unsafe_allow_html=True)
    
    if st.session_state.query_history:
        # Convert to dataframe
        history_df = pd.DataFrame(st.session_state.query_history)
        
        # Display
        st.dataframe(
            history_df,
            column_config={
                "timestamp": st.column_config.TextColumn("Time"),
                "query": st.column_config.TextColumn("Query"),
                "status": st.column_config.TextColumn("Status")
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Clear button
        if st.button("Clear History", type="secondary"):
            st.session_state.query_history = []
            st.rerun()
    else:
        st.info("No query history yet.")

if __name__ == "__main__":
    main()