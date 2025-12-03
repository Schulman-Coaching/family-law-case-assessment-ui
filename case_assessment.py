#!/usr/bin/env python3
"""
Family Law Case Assessment Assistant
For New York Family Law Practice
Identifies: Domestic violence, urgent support needs, hidden assets, jurisdictional issues
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import spacy
from dataclasses import dataclass, asdict

# Load NLP model for text analysis
try:
    nlp = spacy.load("en_core_web_sm")
except:
    print("Note: spaCy model not found. Install with: python -m spacy download en_core_web_sm")
    nlp = None

@dataclass
class ClientIntake:
    """Data structure for client intake information"""
    client_id: str
    client_name: str
    intake_date: str
    marital_status: str
    has_children: bool
    children_info: List[Dict]
    residences: Dict[str, str]  # client and spouse addresses
    emergency_concerns: List[str]
    financial_disclosure: Dict[str, Any]
    notes: str
    opposing_party_info: Dict[str, str]

@dataclass
class AssessmentResult:
    """Results from case assessment"""
    urgency_level: str  # "HIGH", "MEDIUM", "LOW"
    immediate_issues: List[Dict]
    jurisdiction_recommendation: Dict[str, str]
    recommended_actions: List[str]
    flagged_keywords: Dict[str, List[str]]

class CaseAssessmentTool:
    """Main tool for assessing family law cases"""

    # New York County definitions and rules
    NY_COUNTIES = {
        "New York": "Manhattan",
        "Kings": "Brooklyn",
        "Queens": "Queens",
        "Bronx": "Bronx",
        "Richmond": "Staten Island",
        "Westchester": "Westchester",
        "Nassau": "Nassau",
        "Suffolk": "Suffolk",
        "Rockland": "Rockland",
        "Erie": "Buffalo area"
    }

    # Keywords for issue detection
    DOMESTIC_VIOLENCE_KEYWORDS = [
        'abuse', 'violent', 'hit', 'punch', 'slap', 'threat', 'fear', 'scared',
        'restraining order', 'order of protection', 'harass', 'stalk', 'intimidate',
        'weapon', 'gun', 'hurt', 'bruise', 'injury', 'emergency', 'police', '911',
        'control', 'manipulate', 'isolate', 'coerce'
    ]

    URGENT_SUPPORT_KEYWORDS = [
        'no money', 'unemployed', 'jobless', 'eviction', 'homeless', 'hungry',
        'utilities', 'electricity', 'gas', 'water', 'shut off', 'medication',
        'medical', 'treatment', 'urgent', 'immediate', 'desperate', 'crisis',
        'bills', 'debt', 'credit', 'overdue', 'foreclosure'
    ]

    HIDDEN_ASSET_INDICATORS = [
        'offshore', 'crypto', 'bitcoin', 'hidden', 'secret', 'undisclosed',
        'cash business', 'tips', 'under the table', 'unreported',
        'business account', 'side business', 'consulting', 'freelance',
        'foreign account', 'swiss', 'cayman', 'transferred', 'moved money',
        'gifted', 'gave away', 'sold quickly', 'antiques', 'art', 'collectibles',
        'safe deposit', 'safe', 'family loan', 'repayment'
    ]

    JURISDICTION_KEYWORDS = {
        'lived': ['residence', 'live', 'reside', 'address', 'home'],
        'married': ['married', 'wedding', 'ceremony'],
        'children': ['school', 'enrolled', 'pediatrician', 'doctor']
    }

    def __init__(self):
        self.results_history = []

    def analyze_text_for_issues(self, text: str) -> Dict[str, List[str]]:
        """Analyze text content for flagged keywords and issues"""
        text_lower = text.lower()

        flagged = {
            'domestic_violence': [],
            'urgent_support': [],
            'hidden_assets': [],
            'jurisdiction_clues': []
        }

        # Check for domestic violence indicators
        for keyword in self.DOMESTIC_VIOLENCE_KEYWORDS:
            if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
                flagged['domestic_violence'].append(keyword)

        # Check for urgent support needs
        for keyword in self.URGENT_SUPPORT_KEYWORDS:
            if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
                flagged['urgent_support'].append(keyword)

        # Check for hidden asset indicators
        for keyword in self.HIDDEN_ASSET_INDICATORS:
            if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
                flagged['hidden_assets'].append(keyword)

        # Use NLP if available for more sophisticated analysis
        if nlp and text:
            doc = nlp(text)
            # Extract entities for jurisdiction clues
            for ent in doc.ents:
                if ent.label_ in ['GPE', 'LOC']:  # Geo-political entities and locations
                    flagged['jurisdiction_clues'].append(f"{ent.text} ({ent.label_})")

        return flagged

    def determine_jurisdiction(self, intake: ClientIntake) -> Dict[str, str]:
        """Determine proper New York county for filing based on residency rules"""

        # Extract addresses
        client_addr = intake.residences.get('client', '').lower()
        spouse_addr = intake.residences.get('spouse', '').lower()

        jurisdiction = {
            'recommended_county': None,
            'basis': [],
            'issues': [],
            'client_residence': client_addr,
            'spouse_residence': spouse_addr
        }

        # Check for county names in addresses
        county_found = None
        for county, common_name in self.NY_COUNTIES.items():
            county_lower = county.lower()
            common_lower = common_name.lower()

            if (county_lower in client_addr or common_lower in client_addr):
                county_found = county
                jurisdiction['basis'].append(f"Client resides in {county} County")
                break
            elif (county_lower in spouse_addr or common_lower in spouse_addr):
                county_found = county
                jurisdiction['basis'].append(f"Spouse resides in {county} County")
                break

        # NY Domestic Relations Law § 230 - Venue rules
        if county_found:
            jurisdiction['recommended_county'] = county_found
        else:
            jurisdiction['issues'].append("Cannot determine county from addresses provided")
            jurisdiction['recommended_county'] = "New York"  # Default to Manhattan

        # Check if parties live in different counties
        if client_addr and spouse_addr:
            client_county = None
            spouse_county = None

            for county in self.NY_COUNTIES:
                if county.lower() in client_addr:
                    client_county = county
                if county.lower() in spouse_addr:
                    spouse_county = county

            if client_county and spouse_county and client_county != spouse_county:
                jurisdiction['issues'].append(f"Parties live in different counties: {client_county} vs {spouse_county}")
                jurisdiction['basis'].append(f"Multiple jurisdictions possible - may file in either county per DRL §230")

        # Check for children's residence
        if intake.has_children and intake.children_info:
            for child in intake.children_info:
                if 'school' in child:
                    jurisdiction['basis'].append(f"Child attends school: {child.get('school', 'Unknown')}")

        return jurisdiction

    def assess_urgency(self, flagged_issues: Dict[str, List[str]]) -> Tuple[str, List[Dict]]:
        """Determine urgency level and specific immediate issues"""

        immediate_issues = []
        severity_score = 0

        # Domestic violence - highest priority
        if flagged_issues['domestic_violence']:
            severity_score += 10
            immediate_issues.append({
                'type': 'DOMESTIC_VIOLENCE',
                'severity': 'HIGH',
                'indicators': flagged_issues['domestic_violence'][:5],  # First 5 indicators
                'action': 'Immediate referral for Order of Protection. Safety planning required.'
            })

        # Urgent support needs
        if flagged_issues['urgent_support']:
            severity_score += 7
            immediate_issues.append({
                'type': 'URGENT_SUPPORT_NEEDS',
                'severity': 'HIGH',
                'indicators': flagged_issues['urgent_support'][:5],
                'action': 'Consider immediate Pendente Lite motion for temporary support/maintenance.'
            })

        # Hidden assets
        if flagged_issues['hidden_assets']:
            severity_score += 5
            immediate_issues.append({
                'type': 'POTENTIAL_HIDDEN_ASSETS',
                'severity': 'MEDIUM',
                'indicators': flagged_issues['hidden_assets'][:5],
                'action': 'Requires detailed forensic discovery. Consider subpoenas for bank/business records.'
            })

        # Determine urgency level
        if severity_score >= 10:
            urgency = "HIGH"
        elif severity_score >= 5:
            urgency = "MEDIUM"
        else:
            urgency = "LOW"

        return urgency, immediate_issues

    def generate_recommended_actions(self, intake: ClientIntake,
                                   flagged_issues: Dict[str, List[str]],
                                   immediate_issues: List[Dict]) -> List[str]:
        """Generate specific recommended actions for the attorney"""

        actions = []

        # Standard initial actions
        actions.append("Schedule initial client meeting to review concerns in detail")
        actions.append("Complete conflict check for all parties mentioned")
        actions.append("Prepare retainer agreement for client review")

        # Issue-specific actions
        if flagged_issues['domestic_violence']:
            actions.append("IMMEDIATE: Discuss Order of Protection options (Family Court vs Supreme Court)")
            actions.append("Provide client with domestic violence resources and safety plan")
            actions.append("Document all incidents with dates, times, and evidence")

        if flagged_issues['urgent_support']:
            actions.append("Prepare financial affidavit for temporary support motion")
            actions.append("Gather proof of income/expenses for both parties")
            actions.append("Consider emergency motion for temporary relief")

        if flagged_issues['hidden_assets']:
            actions.append("Draft comprehensive discovery demands for financial documents")
            actions.append("Consider need for forensic accountant")
            actions.append("Research business interests and asset searches")

        # Jurisdictional actions
        if intake.residences.get('client') and intake.residences.get('spouse'):
            actions.append("Verify residency requirements for chosen jurisdiction")

        # Children-related actions
        if intake.has_children:
            actions.append("Schedule child custody/visitation planning meeting")
            actions.append("Gather school/medical records for children")
            actions.append("Consider need for parenting coordinator or evaluation")

        return actions

    def assess_case(self, intake_data: Dict) -> AssessmentResult:
        """Main assessment function"""

        # Convert to ClientIntake object
        intake = ClientIntake(**intake_data)

        # Analyze text content
        all_text = f"{intake.notes} {' '.join(intake.emergency_concerns)}"
        flagged_issues = self.analyze_text_for_issues(all_text)

        # Determine jurisdiction
        jurisdiction = self.determine_jurisdiction(intake)

        # Assess urgency and immediate issues
        urgency, immediate_issues = self.assess_urgency(flagged_issues)

        # Generate recommended actions
        recommended_actions = self.generate_recommended_actions(intake, flagged_issues, immediate_issues)

        # Create result object
        result = AssessmentResult(
            urgency_level=urgency,
            immediate_issues=immediate_issues,
            jurisdiction_recommendation=jurisdiction,
            recommended_actions=recommended_actions,
            flagged_keywords=flagged_issues
        )

        # Save to history
        self.results_history.append({
            'client_id': intake.client_id,
            'client_name': intake.client_name,
            'assessment_date': datetime.now().isoformat(),
            'result': asdict(result)
        })

        return result

    def generate_assessment_report(self, result: AssessmentResult,
                                 intake: ClientIntake) -> str:
        """Generate a formatted assessment report"""

        report = []
        report.append("=" * 60)
        report.append("FAMILY LAW CASE ASSESSMENT REPORT")
        report.append("=" * 60)
        report.append(f"Client: {intake.client_name}")
        report.append(f"Client ID: {intake.client_id}")
        report.append(f"Assessment Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("")

        # Urgency Level
        report.append("URGENCY LEVEL:")
        report.append(f"  {result.urgency_level} PRIORITY")
        report.append("")

        # Immediate Issues
        if result.immediate_issues:
            report.append("IMMEDIATE ISSUES IDENTIFIED:")
            for issue in result.immediate_issues:
                report.append(f"  • {issue['type']} ({issue['severity']})")
                report.append(f"    Indicators: {', '.join(issue['indicators'][:3])}")
                report.append(f"    Action: {issue['action']}")
                report.append("")

        # Jurisdiction
        report.append("JURISDICTION ANALYSIS:")
        report.append(f"  Recommended County: {result.jurisdiction_recommendation['recommended_county']}")
        if result.jurisdiction_recommendation['basis']:
            report.append("  Basis:")
            for basis in result.jurisdiction_recommendation['basis']:
                report.append(f"    • {basis}")
        if result.jurisdiction_recommendation['issues']:
            report.append("  Issues/Notes:")
            for issue in result.jurisdiction_recommendation['issues']:
                report.append(f"    • {issue}")
        report.append("")

        # Recommended Actions
        report.append("RECOMMENDED ACTIONS:")
        for i, action in enumerate(result.recommended_actions, 1):
            report.append(f"  {i}. {action}")
        report.append("")

        # Flagged Keywords Summary
        report.append("KEYWORD ANALYSIS SUMMARY:")
        for category, keywords in result.flagged_keywords.items():
            if keywords:
                cat_name = category.replace('_', ' ').title()
                report.append(f"  {cat_name}: {len(keywords)} indicators found")

        return "\n".join(report)

def create_sample_intake() -> Dict:
    """Create a sample intake for testing"""
    return {
        'client_id': 'FL-2023-001',
        'client_name': 'Jane Smith',
        'intake_date': '2023-10-26',
        'marital_status': 'Married',
        'has_children': True,
        'children_info': [
            {'name': 'Child1', 'age': 8, 'school': 'PS 321 Brooklyn'},
            {'name': 'Child2', 'age': 5, 'school': 'PS 321 Brooklyn'}
        ],
        'residences': {
            'client': '123 Main St, Brooklyn, NY 11201',
            'spouse': '456 Park Ave, Manhattan, NY 10022'
        },
        'emergency_concerns': [
            'Husband threatened me with violence',
            'I have no access to bank accounts',
            'He has a secret crypto account',
            'Facing eviction next month'
        ],
        'financial_disclosure': {
            'income': 45000,
            'spouse_income': 250000,
            'joint_assets': 750000,
            'separate_assets': 50000
        },
        'notes': """Client reports escalating arguments with spouse. Spouse has been violent on two occasions, leaving bruises. Client fears for safety. Spouse controls all finances and client has no access to funds. Client discovered Bitcoin account in spouse's name but cannot access. Spouse has consulting business that may have unreported income. Children attend school in Brooklyn. Client wants to file for divorce but fears retaliation.""",
        'opposing_party_info': {
            'name': 'John Smith',
            'employer': 'Self-employed consultant',
            'attorney': 'Unknown'
        }
    }

def main():
    """Main function to demonstrate the tool"""

    print("Family Law Case Assessment Tool - New York")
    print("=" * 50)

    # Initialize tool
    tool = CaseAssessmentTool()

    # Load sample intake
    intake_data = create_sample_intake()

    print("\nAnalyzing client intake...")
    print(f"Client: {intake_data['client_name']}")

    # Perform assessment
    result = tool.assess_case(intake_data)

    # Generate and display report
    intake_obj = ClientIntake(**intake_data)
    report = tool.generate_assessment_report(result, intake_obj)
    print("\n" + report)

    # Optional: Save to file
    save_choice = input("\nSave report to file? (y/n): ")
    if save_choice.lower() == 'y':
        filename = f"case_assessment_{intake_data['client_id']}_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(filename, 'w') as f:
            f.write(report)
        print(f"Report saved to {filename}")

    # Optional: Export as JSON
    export_choice = input("Export assessment as JSON? (y/n): ")
    if export_choice.lower() == 'y':
        json_data = {
            'intake': intake_data,
            'assessment': asdict(result),
            'metadata': {
                'tool_version': '1.0',
                'assessment_date': datetime.now().isoformat()
            }
        }
        json_filename = f"assessment_{intake_data['client_id']}.json"
        with open(json_filename, 'w') as f:
            json.dump(json_data, f, indent=2)
        print(f"JSON exported to {json_filename}")

if __name__ == "__main__":
    # Installation instructions
    print("\n" + "="*60)
    print("INSTALLATION INSTRUCTIONS:")
    print("="*60)
    print("1. Install required packages:")
    print("   pip install spacy")
    print("   python -m spacy download en_core_web_sm")
    print("\n2. Optional: For GUI version, also install:")
    print("   pip install streamlit pandas")
    print("\n3. Run the tool:")
    print("   python case_assessment.py")
    print("="*60 + "\n")

    # Uncomment to run automatically
    # main()
