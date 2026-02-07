import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

class COREPAssistant:
    def __init__(self):
        """Initialize the COREP assistant"""
        self.groq_key = os.getenv("GROQ_API_KEY")
        if not self.groq_key:
            raise ValueError("❌ GROQ_API_KEY not found in .env file")
        
        self.client = Groq(api_key=self.groq_key)
        
        # Load all required files
        self.rules = self.load_file("rules.txt")
        self.schema = self.load_json_file("schema_c0100.json")
        self.validation_rules = self.load_json_file("validation_rules.json")
        
        print("✅ COREP Assistant initialized successfully")
        
    def load_file(self, filename):
        """Load text file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"⚠️ File not found: {filename}")
            return ""
    
    def load_json_file(self, filename):
        """Load JSON file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ JSON file not found: {filename}")
            return {}
    
    def generate_corep_prompt(self, user_scenario):
        """Generate prompt for LLM"""
        
        prompt = f"""You are a PRA COREP regulatory reporting assistant. Your task is to populate the COREP Own Funds template (C 01.00) based on the user's scenario.

REGULATORY RULES:
{self.rules}

COREP TEMPLATE SCHEMA (C 01.00 - CET1 Section):
{json.dumps(self.schema['sections']['CET1_Capital'], indent=2)}

USER SCENARIO:
{user_scenario}

INSTRUCTIONS:
1. Extract numerical values from the scenario
2. Apply COREP reporting rules exactly as specified
3. Calculate total CET1 capital (Row 100) = 010 + 020 + 030 + 040 - 070
4. Flag any missing or inconsistent data
5. Provide audit trail with specific rule references
6. Format all amounts as numbers without commas or currency symbols

REQUIRED OUTPUT FORMAT (JSON ONLY):
{{
  "template": "C 01.00",
  "reporting_date": "2024-12-31",
  "currency": "GBP",
  "data": {{
    "010": {{"value": "150000000", "description": "Ordinary share capital"}},
    "020": {{"value": "75000000", "description": "Share premium account"}},
    "030": {{"value": "300000000", "description": "Retained earnings"}},
    "040": {{"value": "25000000", "description": "Other comprehensive income"}},
    "070": {{"value": "45000000", "description": "Intangible assets (deduction)", "is_deduction": true}},
    "100": {{"value": "505000000", "description": "Total CET1 capital", "is_calculated": true}}
  }},
  "calculations": {{
    "CET1_formula": "010 + 020 + 030 + 040 - 070 = 150M + 75M + 300M + 25M - 45M = 505M"
  }},
  "audit_trail": [
    {{"field": "010", "rule": "CRR Article 26(1)(a)", "justification": "Ordinary shares are CET1 eligible capital"}},
    {{"field": "070", "rule": "CRR Article 36(1)(b)", "justification": "Intangible assets must be deducted from CET1"}}
  ],
  "validation_notes": [
    {{"type": "INFO", "message": "All required fields present", "fields": ["010", "020", "030", "100"]}}
  ]
}}

Return ONLY valid JSON. No explanations, no markdown, no additional text."""

        return prompt
    
    def call_llm(self, prompt):
        """Call Groq LLM API"""
        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-20b", 
                messages=[
                    {"role": "system", "content": "You are a regulatory reporting expert. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"❌ Error calling LLM: {e}")
            return None
    
    def parse_llm_response(self, response_text):
        """Parse and validate LLM response"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
            print(f"Response text: {response_text[:500]}...")
            return None
    
    def validate_response(self, llm_data):
        """Validate the LLM response against schema and rules"""
        
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ["010", "020", "030", "100"]
        for field_code in required_fields:
            if field_code not in llm_data.get("data", {}):
                errors.append(f"Missing required field: {field_code}")
            elif not llm_data["data"][field_code].get("value"):
                warnings.append(f"Empty value for field: {field_code}")
        
        # Check data types
        for field_code, field_data in llm_data.get("data", {}).items():
            value = field_data.get("value", "")
            if value and not re.match(r'^-?\d+$', str(value)):
                warnings.append(f"Non-numeric value in field {field_code}: {value}")
        
        # Validate CET1 calculation
        try:
            data = llm_data.get("data", {})
            components = 0
            deductions = 0
            
            # Sum components (positive values)
            for code in ["010", "020", "030", "040"]:
                if code in data:
                    val_str = data[code].get("value", "0")
                    if val_str:
                        components += int(val_str)
            
            # Sum deductions (negative values)
            for code in ["070"]:
                if code in data:
                    val_str = data[code].get("value", "0")
                    if val_str:
                        deductions += int(val_str)
            
            calculated_cet1 = components - deductions
            
            # Get reported CET1
            reported_cet1_str = data.get("100", {}).get("value", "0")
            reported_cet1 = int(reported_cet1_str) if reported_cet1_str else 0
            
            if calculated_cet1 != reported_cet1:
                errors.append(f"CET1 calculation mismatch: Calculated {calculated_cet1:,} vs Reported {reported_cet1:,}")
            
            # Check CET1 positivity
            if reported_cet1 < 0:
                errors.append(f"CET1 is negative: {reported_cet1:,}")
                
        except ValueError as e:
            warnings.append(f"Calculation error: {e}")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "is_valid": len(errors) == 0
        }
    
    def display_corep_template(self, llm_data):
        """Display COREP template in human-readable format"""
        
        print("\n" + "="*70)
        print("COREP TEMPLATE C 01.00 - OWN FUNDS (CET1 SECTION)")
        print("="*70)
        print(f"{'Row':<6} {'Description':<35} {'Amount (£)':>20}")
        print("-"*70)
        
        data = llm_data.get("data", {})
        
        # Define display order
        display_order = [
            ("010", "Ordinary share capital"),
            ("020", "Share premium account"),
            ("030", "Retained earnings"),
            ("040", "Other comprehensive income"),
            ("070", "(-) Intangible assets"),
            ("100", "TOTAL CET1 CAPITAL")
        ]
        
        for code, description in display_order:
            if code in data:
                field_info = data[code]
                value_str = field_info.get("value", "0")
                
                try:
                    value = int(value_str) if value_str else 0
                    
                    # Format based on whether it's a deduction
                    if field_info.get("is_deduction", False):
                        formatted = f"({abs(value):,})"
                    else:
                        formatted = f"{value:,}"
                        
                    print(f"{code:<6} {description:<35} {formatted:>20}")
                    
                except ValueError:
                    print(f"{code:<6} {description:<35} {value_str:>20}")
        
        print("-"*70)
        
        # Show calculations if available
        if "calculations" in llm_data:
            print("\n📝 CALCULATIONS:")
            for calc_name, calc_formula in llm_data["calculations"].items():
                print(f"  • {calc_formula}")
    
    def display_audit_trail(self, llm_data):
        """Display audit trail with rule references"""
        
        audit_trail = llm_data.get("audit_trail", [])
        
        if not audit_trail:
            print("\n⚠️ No audit trail provided")
            return
        
        print("\n" + "="*70)
        print("REGULATORY AUDIT TRAIL")
        print("="*70)
        
        for entry in audit_trail:
            field = entry.get("field", "N/A")
            rule = entry.get("rule", "N/A")
            justification = entry.get("justification", "")
            
            print(f"\nField {field}:")
            print(f"  Rule: {rule}")
            print(f"  Basis: {justification}")
    
    def display_validation_results(self, validation_results, llm_data):
        """Display validation results"""
        
        print("\n" + "="*70)
        print("VALIDATION RESULTS")
        print("="*70)
        
        errors = validation_results["errors"]
        warnings = validation_results["warnings"]
        
        if errors:
            print("\n❌ ERRORS:")
            for error in errors:
                print(f"  • {error}")
        
        if warnings:
            print("\n⚠️ WARNINGS:")
            for warning in warnings:
                print(f"  • {warning}")
        
        # Also show validation notes from LLM
        validation_notes = llm_data.get("validation_notes", [])
        if validation_notes:
            print("\n📋 LLM VALIDATION NOTES:")
            for note in validation_notes:
                note_type = note.get("type", "INFO")
                message = note.get("message", "")
                print(f"  [{note_type}] {message}")
        
        if not errors and not warnings:
            print("\n✅ All validation checks passed")
    
    def save_report(self, llm_data, validation_results):
        """Save complete report to file"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"corep_report_{timestamp}.json"
        
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "template": llm_data.get("template", "C 01.00"),
                "assistant_version": "1.0"
            },
            "report_data": llm_data,
            "validation_results": validation_results,
            "summary": {
                "fields_populated": len(llm_data.get("data", {})),
                "has_errors": len(validation_results["errors"]) > 0,
                "has_warnings": len(validation_results["warnings"]) > 0
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Report saved to: {filename}")
        return filename
    
    def run(self):
        """Main execution flow"""
        
        print("\n🏛️ PRA COREP REGULATORY REPORTING ASSISTANT")
        print("="*50)
        
        # Example scenarios
        print("\nExample scenarios you can use:")
        print("1. 'Bank has £150M ordinary shares, £75M share premium, £300M retained earnings, £25M OCI, £45M intangible assets'")
        print("2. 'Calculate CET1 for a bank with £100M shares, £50M premium, £200M earnings, £30M intangibles'")
        print("3. 'What fields are needed for CET1 reporting?'")
        
        # Get user input
        user_input = input("\nEnter your scenario/question: ").strip()
        
        if not user_input:
            # Use default if empty
            user_input = "A UK bank has £150,000,000 ordinary shares, £75,000,000 share premium, £300,000,000 retained earnings, £25,000,000 other comprehensive income, and £45,000,000 intangible assets."
        
        print(f"\n📋 Processing: {user_input[:100]}...")
        
        # Step 1: Generate prompt
        prompt = self.generate_corep_prompt(user_input)
        
        # Step 2: Call LLM
        print("🤖 Querying regulatory assistant...")
        llm_response = self.call_llm(prompt)
        
        if not llm_response:
            print("❌ Failed to get response from LLM")
            return
        
        # Step 3: Parse response
        print("📊 Parsing response...")
        llm_data = self.parse_llm_response(llm_response)
        
        if not llm_data:
            print("❌ Failed to parse LLM response")
            return
        
        # Step 4: Validate
        print("🔍 Validating data...")
        validation_results = self.validate_response(llm_data)
        
        # Step 5: Display results
        print("\n" + "="*70)
        print("📋 REPORT GENERATED SUCCESSFULLY")
        print("="*70)
        
        self.display_corep_template(llm_data)
        self.display_validation_results(validation_results, llm_data)
        self.display_audit_trail(llm_data)
        
        # Step 6: Save report
        self.save_report(llm_data, validation_results)
        
        print("\n" + "="*70)
        print("✅ PROTOTYPE EXECUTION COMPLETE")
        print("="*70)

# Main execution
if __name__ == "__main__":
    try:
        assistant = COREPAssistant()
        assistant.run()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure you have:")
        print("1. .env file with GROQ_API_KEY")
        print("2. rules.txt file")
        print("3. schema_c0100.json file")
        print("4. validation_rules.json file")