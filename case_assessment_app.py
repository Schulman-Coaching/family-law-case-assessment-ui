# file: case_assessment_app.py
import streamlit as st
import pandas as pd
from case_assessment import CaseAssessmentTool, ClientIntake, create_sample_intake

def main():
    st.set_page_config(page_title="Family Law Case Assessment", layout="wide")

    st.title("New York Family Law Case Assessment Tool")
    st.markdown("---")

    # Initialize tool in session state
    if 'tool' not in st.session_state:
        st.session_state.tool = CaseAssessmentTool()

    # Sidebar for navigation
    with st.sidebar:
        st.header("Navigation")
        menu_option = st.radio(
            "Select Option:",
            ["New Assessment", "Load Sample", "View History", "Export Data"]
        )

        st.markdown("---")
        st.info("**Features:**\n"
                "- Domestic violence detection\n"
                "- Urgent support needs flagging\n"
                "- Hidden asset indicators\n"
                "- NY jurisdiction analysis\n"
                "- Action recommendations")

    if menu_option == "New Assessment":
        st.header("New Client Assessment")

        # Input form
        with st.form("intake_form"):
            col1, col2 = st.columns(2)

            with col1:
                client_id = st.text_input("Client ID", value="FL-")
                client_name = st.text_input("Client Name")
                marital_status = st.selectbox(
                    "Marital Status",
                    ["Married", "Separated", "Divorcing", "Never Married"]
                )
                has_children = st.checkbox("Has Children")

            with col2:
                client_address = st.text_input("Client Address")
                spouse_address = st.text_input("Spouse Address")
                emergency_level = st.select_slider(
                    "Emergency Level",
                    options=["Low", "Medium", "High", "Critical"]
                )

            # Emergency concerns
            st.subheader("Emergency Concerns")
            concerns = st.text_area(
                "List immediate concerns (one per line)",
                height=100,
                help="Enter each concern on a new line"
            )

            # Detailed notes
            st.subheader("Case Notes")
            notes = st.text_area(
                "Detailed case notes",
                height=200,
                help="Include all relevant details about the case"
            )

            # Submit button
            submitted = st.form_submit_button("Analyze Case")

            if submitted:
                # Create intake data
                intake_data = {
                    'client_id': client_id,
                    'client_name': client_name,
                    'intake_date': pd.Timestamp.now().strftime('%Y-%m-%d'),
                    'marital_status': marital_status,
                    'has_children': has_children,
                    'children_info': [],
                    'residences': {
                        'client': client_address,
                        'spouse': spouse_address
                    },
                    'emergency_concerns': concerns.split('\n') if concerns else [],
                    'financial_disclosure': {},
                    'notes': notes,
                    'opposing_party_info': {}
                }

                # Perform assessment
                with st.spinner("Analyzing case..."):
                    result = st.session_state.tool.assess_case(intake_data)
                    intake_obj = ClientIntake(**intake_data)

                    # Display results
                    st.success("Assessment Complete!")

                    # Urgency badge
                    urgency_color = {
                        "HIGH": "red",
                        "MEDIUM": "orange",
                        "LOW": "green"
                    }.get(result.urgency_level, "gray")

                    st.markdown(f"""
                    <div style="padding: 10px; border-radius: 5px; background-color: {urgency_color}; color: white; text-align: center;">
                        <h3>Urgency Level: {result.urgency_level}</h3>
                    </div>
                    """, unsafe_allow_html=True)

                    # Create tabs for different sections
                    tab1, tab2, tab3, tab4 = st.tabs([
                        "Immediate Issues",
                        "Jurisdiction",
                        "Recommendations",
                        "Analysis Details"
                    ])

                    with tab1:
                        if result.immediate_issues:
                            for issue in result.immediate_issues:
                                with st.expander(f"{issue['type']} - {issue['severity']}"):
                                    st.write("**Indicators:**", ", ".join(issue['indicators']))
                                    st.write("**Action Required:**", issue['action'])
                        else:
                            st.info("No immediate critical issues detected.")

                    with tab2:
                        st.write("**Recommended County:**",
                                result.jurisdiction_recommendation['recommended_county'])
                        st.write("**Client Address:**",
                                result.jurisdiction_recommendation['client_residence'])
                        st.write("**Spouse Address:**",
                                result.jurisdiction_recommendation['spouse_residence'])

                        if result.jurisdiction_recommendation['basis']:
                            st.write("**Basis for Jurisdiction:**")
                            for basis in result.jurisdiction_recommendation['basis']:
                                st.write(f"- {basis}")

                    with tab3:
                        st.write("**Recommended Actions:**")
                        for i, action in enumerate(result.recommended_actions, 1):
                            st.write(f"{i}. {action}")

                    with tab4:
                        # Keyword analysis
                        st.write("**Keyword Detection Summary:**")
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            dv_count = len(result.flagged_keywords['domestic_violence'])
                            st.metric("Domestic Violence Indicators", dv_count)
                            if dv_count > 0:
                                with st.expander("View indicators"):
                                    for word in result.flagged_keywords['domestic_violence']:
                                        st.write(f"- {word}")

                        with col2:
                            us_count = len(result.flagged_keywords['urgent_support'])
                            st.metric("Urgent Support Indicators", us_count)

                        with col3:
                            ha_count = len(result.flagged_keywords['hidden_assets'])
                            st.metric("Hidden Asset Indicators", ha_count)

                    # Export options
                    st.download_button(
                        label="Download Report",
                        data=st.session_state.tool.generate_assessment_report(result, intake_obj),
                        file_name=f"assessment_{client_id}.txt",
                        mime="text/plain"
                    )

    elif menu_option == "Load Sample":
        st.header("Sample Case Assessment")
        st.info("This demonstrates the tool with sample data. Click 'Analyze Sample' to see results.")

        if st.button("Analyze Sample"):
            with st.spinner("Processing sample case..."):
                intake_data = create_sample_intake()
                result = st.session_state.tool.assess_case(intake_data)
                intake_obj = ClientIntake(**intake_data)

                # Display report
                st.text(st.session_state.tool.generate_assessment_report(result, intake_obj))

    elif menu_option == "View History":
        st.header("Assessment History")
        if st.session_state.tool.results_history:
            # Convert to DataFrame for display
            history_data = []
            for record in st.session_state.tool.results_history:
                history_data.append({
                    'Client ID': record['client_id'],
                    'Client Name': record['client_name'],
                    'Date': record['assessment_date'],
                    'Urgency': record['result']['urgency_level']
                })

            df = pd.DataFrame(history_data)
            st.dataframe(df)
        else:
            st.info("No assessments in history yet.")

    elif menu_option == "Export Data":
        st.header("Export Assessment Data")
        st.info("Export all assessment data for record-keeping or analysis.")

        if st.session_state.tool.results_history:
            # Convert to JSON
            import json
            export_data = {
                'assessments': st.session_state.tool.results_history,
                'export_date': pd.Timestamp.now().isoformat()
            }

            st.download_button(
                label="Export All Data (JSON)",
                data=json.dumps(export_data, indent=2),
                file_name="all_assessments.json",
                mime="application/json"
            )
        else:
            st.warning("No data available to export.")

if __name__ == "__main__":
    main()
