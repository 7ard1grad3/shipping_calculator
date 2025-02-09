import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from app.calculator import ShippingCalculator
from app.data_loader import PricingData
from datetime import datetime
from app.auth import create_login_page, is_authenticated

from configurations import EXCEL_FILE


# Initialize database and calculator
@st.cache_resource
def initialize_calculator():
    pricing_data = PricingData(
        excel_path=f"data/{EXCEL_FILE}",
        db_path="data/shipping.db"
    )
    return ShippingCalculator(pricing_data)


# Load configurations from database
def load_configs():
    configs = calculator.pricing_data.db.get_all_configs()
    return {
        'DEFAULT_WEIGHT_TYPE': configs.get('DEFAULT_WEIGHT_TYPE', 'volume'),
        'NNR_PREMIUM_FEES': float(configs.get('NNR_PREMIUM_FEES', '20.0')),
        'UNILOG_PREMIUM_FEES': float(configs.get('UNILOG_PREMIUM_FEES', '35.0')),
        'FUEL_SURCHARGE': float(configs.get('FUEL_SURCHARGE', '8.0'))
    }


# Set page config
st.set_page_config(
    page_title="CTS Shipping Calculator",
    page_icon="🚚",
    layout="wide"
)

# Check authentication
if not is_authenticated():
    create_login_page()
else:
    # Initialize calculator
    calculator = initialize_calculator()

    # Load configurations from database
    if 'config' not in st.session_state:
        st.session_state.config = load_configs()

    # Load unique countries
    with calculator.pricing_data.db.get_connection() as conn:
        countries_df = pd.read_sql("SELECT DISTINCT country FROM zones ORDER BY country", conn)

    # Tabs for different features
    tab1, tab2, tab3 = st.tabs([
        "Single Calculation",
        "Configurations",
        "Calculation History"
    ])

    # Single Calculation Tab
    with tab1:
        st.header("Shipping Price Calculator")

        # Destination Details
        st.subheader("Destination")
        col1, col2 = st.columns(2)
        with col1:
            country = st.selectbox(
                "Country",
                options=countries_df['country'].tolist(),
                help="Select destination country"
            )

        with col2:
            zipcode = st.text_input(
                "Zip/Postal Code",
                help="Enter destination zip/postal code"
            )

        # Shipment Details
        st.subheader("Shipment Details")
        col1, col2, col3 = st.columns(3)

        with col1:
            service_level = st.selectbox(
                "Service Level",
                options=['Priority', 'Road Express', 'Economy'],
                help="Select shipping service level"
            )

        with col2:
            num_collo = st.number_input(
                "Number of Collo",
                min_value=1,
                value=1,
                step=1,
                help="Enter number of collo"
            )

        with col3:
            actual_weight = st.number_input(
                "Actual Weight (kg)",
                min_value=0.1,
                max_value=1000.0,
                value=1.0,
                step=0.1,
                format="%.1f",
                help="Enter actual weight in kilograms"
            )

        # Package Dimensions
        st.subheader("Package Dimensions (cm)")
        dim_col1, dim_col2, dim_col3 = st.columns(3)
        
        with dim_col1:
            length = st.number_input(
                "Length",
                min_value=1.0,
                max_value=240.0,
                value=100.0,
                help="Enter package length in centimeters (max 240cm)"
            )
            
        with dim_col2:
            width = st.number_input(
                "Width",
                min_value=1.0,
                max_value=120.0,
                value=80.0,
                help="Enter package width in centimeters (max 120cm)"
            )
            
        with dim_col3:
            height = st.number_input(
                "Height",
                min_value=1.0,
                max_value=220.0,
                value=120.0,
                help="Enter package height in centimeters (max 220cm)"
            )

        # Weight Type
        st.subheader("Weight")
        weight_type = st.selectbox(
            "Weight Type",
            options=['volume', 'actual', 'loading_meter'],
            index=['volume', 'actual', 'loading_meter'].index(st.session_state.config['DEFAULT_WEIGHT_TYPE']),
            help="Select weight type for calculation"
        )

        if all([length, width, height]):
            volume_weight = calculator.calculate_volume_weight(num_collo, length, width, height)
            loading_meter_weight = calculator.calculate_loading_meter_weight(num_collo, length, width)

            st.subheader("Calculated Weights")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Actual Weight (kg)", f"{actual_weight:.2f}")
            with col2:
                st.metric("Volume Weight (kg)", f"{volume_weight:.2f}")
            with col3:
                st.metric("Loading Meter Weight (kg)", f"{loading_meter_weight:.2f}")

            if height > 120:
                st.warning("Height exceeds 120cm - Shipment will be calculated as non-stackable")

        if st.button("Calculate Price", type="primary"):
            if not zipcode:
                st.error("Please enter a zip/postal code")
            else:
                try:
                    result = calculator.calculate_price(
                        num_collo=num_collo,
                        length=length,
                        width=width,
                        height=height,
                        actual_weight=actual_weight,
                        country=country,
                        zipcode=zipcode,
                        service_level=service_level,
                        weight_type=weight_type
                    )

                    # Store calculation in history
                    with calculator.pricing_data.db.get_connection() as conn:
                        conn.execute("""
                            INSERT INTO calculation_history (
                                timestamp, country, zipcode, service_level, num_collo,
                                length, width, height,
                                actual_weight, volume_weight, loading_meter_weight,
                                chargeable_weight, weight_type, zone,
                                base_rate, extra_fees, total_price
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            datetime.now().isoformat(),
                            country, zipcode, service_level, num_collo,
                            length, width, height,
                            actual_weight, volume_weight, loading_meter_weight,
                            result['chargeable_weight'], result['weight_type'], result['zone'],
                            result['base_rate'], result['extra_fees'], result['total_price']
                        ))
                        conn.commit()

                    # Display results
                    st.success(f"Using {result['weight_type'].upper()} weight for calculation")

                    # Display zone and weight information
                    st.info(f"""
                    Zone: {result['zone']}
                    Chargeable Weight: {result['chargeable_weight']:.2f} kg
                    Weight Type Used: {result['weight_type'].title()}
                    """)

                    # Price breakdown
                    st.subheader("Price Breakdown")

                    # Create a detailed breakdown table
                    breakdown = result['fee_breakdown']
                    breakdown_data = pd.DataFrame([
                        {"Step": "Base Rate", "Amount": breakdown['base_rate'], "Cumulative": breakdown['base_rate']},
                        {"Step": f"+ NNR Premium ({breakdown['nnr_premium']['percentage']}%)",
                         "Amount": breakdown['nnr_premium']['amount'],
                         "Cumulative": breakdown['base_rate'] + breakdown['nnr_premium']['amount']},
                        {"Step": f"+ Unilog Premium ({breakdown['unilog_premium']['percentage']}%)",
                         "Amount": breakdown['unilog_premium']['amount'],
                         "Cumulative": breakdown['base_rate'] + breakdown['nnr_premium']['amount'] +
                                       breakdown['unilog_premium']['amount']},
                        {"Step": f"+ Fuel Surcharge ({breakdown['fuel_surcharge']['percentage']}%)",
                         "Amount": breakdown['fuel_surcharge']['amount'],
                         "Cumulative": breakdown['final_price']},
                    ])

                    st.dataframe(
                        breakdown_data,
                        column_config={
                            "Step": "Calculation Step",
                            "Amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                            "Cumulative": st.column_config.NumberColumn("Cumulative Total", format="$%.2f")
                        },
                        hide_index=True
                    )

                    # Final price metrics
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Extra Fees", f"${breakdown['total_extra_fees']:.2f}")
                    with col2:
                        st.metric("Final Price", f"${breakdown['final_price']:.2f}")

                except Exception as e:
                    st.error(f"Error calculating price: {str(e)}")

    # Configurations Tab
    with tab2:
        st.header("Configurations")

        with st.form("config_form"):
            st.subheader("Default Settings")

            default_weight_type = st.selectbox(
                "Default Weight Type",
                options=['volume', 'actual', 'loading_meter'],
                index=['volume', 'actual', 'loading_meter'].index(st.session_state.config['DEFAULT_WEIGHT_TYPE']),
                help="Select the default weight type for calculations"
            )

            st.subheader("Fee Settings")
            nnr_premium = st.number_input(
                "NNR Premium Fees (%)",
                value=float(st.session_state.config['NNR_PREMIUM_FEES']),
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.1f",
                help="Set the NNR Premium Fees percentage"
            )

            unilog_premium = st.number_input(
                "Unilog Premium Fees (%)",
                value=float(st.session_state.config['UNILOG_PREMIUM_FEES']),
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.1f",
                help="Set the Unilog Premium Fees percentage"
            )

            fuel_surcharge = st.number_input(
                "Fuel Surcharge (%)",
                value=float(st.session_state.config['FUEL_SURCHARGE']),
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.1f",
                help="Set the Fuel Surcharge percentage"
            )

            if st.form_submit_button("Save Configuration"):
                # Save to database
                db = calculator.pricing_data.db
                db.set_config('DEFAULT_WEIGHT_TYPE', default_weight_type)
                db.set_config('NNR_PREMIUM_FEES', str(nnr_premium))
                db.set_config('UNILOG_PREMIUM_FEES', str(unilog_premium))
                db.set_config('FUEL_SURCHARGE', str(fuel_surcharge))

                # Update session state
                st.session_state.config.update({
                    'DEFAULT_WEIGHT_TYPE': default_weight_type,
                    'NNR_PREMIUM_FEES': float(nnr_premium),
                    'UNILOG_PREMIUM_FEES': float(unilog_premium),
                    'FUEL_SURCHARGE': float(fuel_surcharge)
                })

                st.success("Configuration saved successfully!")

        # Show configuration history
        st.subheader("Configuration History")
        with calculator.pricing_data.db.get_connection() as conn:
            history_df = pd.read_sql("""
                SELECT name, value, updated_at
                FROM configurations
                ORDER BY updated_at DESC
            """, conn)

            st.dataframe(
                history_df,
                column_config={
                    "name": "Setting",
                    "value": "Value",
                    "updated_at": "Last Updated"
                }
            )

    # Calculation History Tab
    with tab3:
        st.header("Calculation History")

        history = calculator.pricing_data.db.get_calculation_history()
        if not history:
            st.info("No calculations yet")
        else:
            history_df = pd.DataFrame(history)

            # Display summary statistics
            st.subheader("Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Calculations", len(history_df))
            with col2:
                st.metric("Average Price", f"${history_df['total_price'].mean():.2f}")
            with col3:
                st.metric("Total Revenue", f"${history_df['total_price'].sum():.2f}")

            # Timeline chart
            st.subheader("Price History")
            fig = px.line(
                history_df,
                x='timestamp',
                y='total_price',
                hover_data=['country', 'zipcode', 'service_level', 'weight_type'],
                title='Price History Over Time'
            )
            st.plotly_chart(fig)

            # Full history table
            st.subheader("Detailed History")
            st.dataframe(
                history_df[[
                    'timestamp', 'country', 'zipcode', 'service_level', 'num_collo',
                    'actual_weight', 'loading_meter_weight', 'weight_type', 
                    'base_rate', 'extra_fees', 'total_price', 'zone',
                    'length', 'width', 'height'
                ]].sort_values('timestamp', ascending=False)
                .style.format({
                    'actual_weight': '{:.2f} kg',
                    'loading_meter_weight': '{:.2f} kg',
                    'base_rate': '€{:.2f}',
                    'extra_fees': '€{:.2f}',
                    'total_price': '€{:.2f}',
                    'length': '{:.1f} cm',
                    'width': '{:.1f} cm',
                    'height': '{:.1f} cm'
                })
            )

            # Export option
            if st.button("Export History"):
                csv = history_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name="calculation_history.csv",
                    mime="text/csv"
                )

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <p>CTS Shipping Calculator v1.0</p>
    </div>
    """, unsafe_allow_html=True)