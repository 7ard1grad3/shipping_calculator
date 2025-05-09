import streamlit as st

# Set page config
st.set_page_config(
    page_title="Shipping Calculator",
    page_icon="🚚",
    layout="wide"
)

import pandas as pd
import plotly.express as px
from pathlib import Path
from app.calculator import ShippingCalculator
from app.data_loader import PricingData
from datetime import datetime
from app.auth import create_login_page, is_authenticated
from app.utils.log_reader import LogReader

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


# Initialize calculator
calculator = initialize_calculator()

# Load initial configurations
configs = load_configs()

# Custom CSS for better styling
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 16px;
        font-weight: 500;
    }
    div[data-testid="stExpander"] div[role="button"] p {
        font-size: 16px;
        font-weight: 500;
    }
    .stButton button {
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

def main():
    # Title
    st.title("🚚 Shipping Calculator")
    
    # Authentication
    if not is_authenticated():
        create_login_page()
        return

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Calculator", "⚙️ Configurations", "📜 History", "📋 API Logs"])
    
    with tab1:
        st.markdown("### Calculate Shipping Costs")
        
        # Destination Details
        st.subheader("Destination")
        col1, col2 = st.columns(2)
        with col1:
            country = st.selectbox(
                "Country",
                options=calculator.pricing_data.db.get_unique_countries(),
                help="Select destination country"
            )

        with col2:
            zipcode = st.text_input(
                "Zip/Postal Code",
                help="Enter destination zip/postal code"
            )

        # Shipment Details
        st.subheader("Shipment Details")
        col1, col2 = st.columns(2)

        with col1:
            num_collo = st.number_input(
                "Number of Collo",
                min_value=1,
                value=1,
                step=1,
                help="Enter number of collo"
            )

        with col2:
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

        if st.button("Calculate Prices", type="primary"):
            try:
                # Calculate prices for all service levels
                results = {}
                errors = {}
                
                for service_level in ['Economy', 'Road Express', 'Priority']:
                    try:
                        result = calculator.calculate_price(
                            num_collo=num_collo,
                            length=length,
                            width=width,
                            height=height,
                            actual_weight=actual_weight,
                            country=country,
                            zipcode=zipcode,
                            service_level=service_level
                        )
                        results[service_level] = result

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
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                country, zipcode, service_level, num_collo,
                                length, width, height,
                                actual_weight, volume_weight, loading_meter_weight,
                                result['chargeable_weight'], result['weight_type'], result['zone'],
                                result['base_rate'], result['extra_fees'], result['total_price']
                            ))
                            conn.commit()
                    except ValueError as e:
                        errors[service_level] = str(e)
                    except Exception as e:
                        errors[service_level] = f"Unexpected error: {str(e)}"

                if not results:
                    st.markdown(
                        '<div class="warning-box">No service levels available for the given parameters.</div>',
                        unsafe_allow_html=True
                    )
                    st.error("Errors encountered:")
                    for service, error in errors.items():
                        st.error(f"{service}: {error}")
                else:
                    # Show warning for unavailable services
                    if errors:
                        st.markdown(
                            '<div class="warning-box">Some service levels are not available:</div>',
                            unsafe_allow_html=True
                        )
                        for service, error in errors.items():
                            st.warning(f"{service}: {error}")
                    
                    # Display results for available service levels
                    first_result = next(iter(results.values()))
                    st.markdown(
                        f'<div class="success-box">Using {first_result["weight_type"].upper()} weight for calculation</div>',
                        unsafe_allow_html=True
                    )
                    
                    st.markdown("### 💰 Available Shipping Prices")
                    
                    # Create price cards in a grid
                    num_cols = len(results)
                    cols = st.columns(num_cols)
                    for idx, (service, result) in enumerate(results.items()):
                        with cols[idx]:
                            with st.expander(f"{service} - €{result['total_price']:.2f}", expanded=False):
                                st.markdown(f"**Zone:** {result['zone']}")
                                
                                # Base rate
                                st.markdown("##### Base Rate")
                                st.markdown(f"€{result['base_rate']:.2f}")
                                
                                # Extra fees breakdown
                                st.markdown("##### Extra Fees Breakdown")
                                breakdown = result['fee_breakdown']
                                
                                # Create a clean fees table
                                fee_data = {
                                    "Fee Type": ["NNR Premium", "Unilog Premium", "Fuel Surcharge"],
                                    "Percentage": [
                                        f"{breakdown['nnr_premium']['percentage']}%",
                                        f"{breakdown['unilog_premium']['percentage']}%",
                                        f"{breakdown['fuel_surcharge']['percentage']}%"
                                    ],
                                    "Amount": [
                                        f"€{breakdown['nnr_premium']['amount']:.2f}",
                                        f"€{breakdown['unilog_premium']['amount']:.2f}",
                                        f"€{breakdown['fuel_surcharge']['amount']:.2f}"
                                    ]
                                }
                                st.table(pd.DataFrame(fee_data))
                                
                                # Total
                                st.markdown("##### Total")
                                st.markdown(f"""
                                | Type | Amount |
                                |------|--------|
                                | Extra Fees | €{breakdown['total_extra_fees']:.2f} |
                                | Final Price | €{breakdown['final_price']:.2f} |
                                """)

            except ValueError as e:
                st.markdown(f'<div class="warning-box">{str(e)}</div>', unsafe_allow_html=True)

    with tab2:
        st.header("Configurations")

        with st.form("config_form"):
            st.subheader("Default Settings")

            default_weight_type = st.selectbox(
                "Default Weight Type",
                options=['volume', 'actual', 'loading_meter'],
                index=['volume', 'actual', 'loading_meter'].index(configs['DEFAULT_WEIGHT_TYPE']),
                help="Select the default weight type for calculations"
            )

            st.subheader("Fee Settings")
            nnr_premium = st.number_input(
                "NNR Premium Fees (%)",
                value=float(configs['NNR_PREMIUM_FEES']),
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.1f",
                help="Set the NNR Premium Fees percentage"
            )

            unilog_premium = st.number_input(
                "Unilog Premium Fees (%)",
                value=float(configs['UNILOG_PREMIUM_FEES']),
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.1f",
                help="Set the Unilog Premium Fees percentage"
            )

            fuel_surcharge = st.number_input(
                "Fuel Surcharge (%)",
                value=float(configs['FUEL_SURCHARGE']),
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
                configs.update({
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

    with tab3:
        st.header("Calculation History")

        history = calculator.pricing_data.db.get_calculation_history()
        if not history:
            st.info("No calculations yet")
        else:
            history_df = pd.DataFrame(history)

            # Calculate metrics
            country_data = []
            for country in history_df['country'].unique():
                country_rows = history_df[history_df['country'] == country]
                country_data.append({
                    'country': country,
                    'count': len(country_rows),
                    'total_price': country_rows['total_price'].sum()
                })
            country_stats = pd.DataFrame(country_data)
            country_stats = country_stats.sort_values('total_price', ascending=False).head(3)
            
            zone_data = []
            for zone in history_df['zone'].unique():
                zone_rows = history_df[history_df['zone'] == zone]
                zone_data.append({
                    'zone': zone,
                    'count': len(zone_rows),
                    'total_price': zone_rows['total_price'].sum()
                })
            zone_stats = pd.DataFrame(zone_data)
            zone_stats = zone_stats.sort_values('total_price', ascending=False).head(3)
            
            avg_weight = history_df['loading_meter_weight'].mean()
            
            # Display metrics in columns
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**🌍 Top Countries**")
                for _, row in country_stats.iterrows():
                    st.markdown(f"{row['country']}: {row['count']} shipments (€{row['total_price']:.2f})")
            
            with col2:
                st.markdown("**📦 Average Loading Meter Weight**")
                st.markdown(f"{avg_weight:.2f} kg")
            
            with col3:
                st.markdown("**🎯 Top Zones**")
                for _, row in zone_stats.iterrows():
                    st.markdown(f"{row['zone']}: {row['count']} shipments (€{row['total_price']:.2f})")

            # Timeline charts
            st.subheader("Price History")
            col1, col2 = st.columns(2)
            
            # Prepare data for plotting
            plot_df = history_df.copy()
            # Convert timestamp with a more flexible parser
            plot_df['timestamp'] = pd.to_datetime(plot_df['timestamp'], format='mixed')
            plot_df = plot_df.sort_values('timestamp')
            
            # Create figure for price history
            with col1:
                fig_price = px.scatter(
                    plot_df,
                    x='timestamp',
                    y='total_price',
                    color='service_level',
                    title='Price History Over Time',
                    labels={'total_price': 'Price (€)', 'timestamp': 'Date', 'service_level': 'Service Level'}
                )
                
                # Add lines connecting points for each service level
                for service in ['Economy', 'Road Express', 'Priority']:
                    service_data = plot_df[plot_df['service_level'] == service]
                    if not service_data.empty:
                        fig_price.add_scatter(
                            x=service_data['timestamp'],
                            y=service_data['total_price'],
                            mode='lines',
                            line=dict(shape='linear'),
                            name=service,
                            showlegend=False
                        )
                
                fig_price.update_layout(
                    yaxis_title='Price (€)',
                    xaxis_title='Date',
                    legend_title='Service Level',
                    hovermode='x unified'
                )
                fig_price.update_traces(
                    hovertemplate='<br>'.join([
                        'Date: %{x}',
                        'Price: €%{y:.2f}',
                        'Country: %{customdata[0]}',
                        'Zipcode: %{customdata[1]}',
                        'Weight Type: %{customdata[2]}'
                    ]),
                    customdata=plot_df[['country', 'zipcode', 'weight_type']]
                )
                st.plotly_chart(fig_price, use_container_width=True)
            
            # Create figure for loading meter weight
            with col2:
                fig_weight = px.scatter(
                    plot_df,
                    x='timestamp',
                    y='loading_meter_weight',
                    color='service_level',
                    title='Loading Meter Weight History',
                    labels={'loading_meter_weight': 'Weight (kg)', 'timestamp': 'Date', 'service_level': 'Service Level'}
                )
                
                # Add lines connecting points for each service level
                for service in ['Economy', 'Road Express', 'Priority']:
                    service_data = plot_df[plot_df['service_level'] == service]
                    if not service_data.empty:
                        fig_weight.add_scatter(
                            x=service_data['timestamp'],
                            y=service_data['loading_meter_weight'],
                            mode='lines',
                            line=dict(shape='linear'),
                            name=service,
                            showlegend=False
                        )
                
                fig_weight.update_layout(
                    yaxis_title='Weight (kg)',
                    xaxis_title='Date',
                    legend_title='Service Level',
                    hovermode='x unified'
                )
                fig_weight.update_traces(
                    hovertemplate='<br>'.join([
                        'Date: %{x}',
                        'Weight: %{y:.2f} kg',
                        'Country: %{customdata[0]}',
                        'Zipcode: %{customdata[1]}',
                        'Weight Type: %{customdata[2]}'
                    ]),
                    customdata=plot_df[['country', 'zipcode', 'weight_type']]
                )
                st.plotly_chart(fig_weight, use_container_width=True)

            # Full history table
            st.subheader("Detailed History")
            col1, col2 = st.columns([1, 10])
            with col1:
                # Clear history button
                if st.button("🗑️ Clear History"):
                    with calculator.pricing_data.db.get_connection() as conn:
                        conn.execute("DELETE FROM calculation_history")
                        conn.commit()
                    st.rerun()
                
                # Export button
                csv = history_df.to_csv(index=False)
                st.download_button(
                    label="📥 Export History",
                    data=csv,
                    file_name='shipping_calculation_history.csv',
                    mime='text/csv',
                )
            with col2:
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

    with tab4:
        st.markdown("### Teldor API Request Logs")
        
        # Initialize log reader
        log_reader = LogReader()
        
        # Add refresh button
        if st.button("Refresh Logs", key="refresh_logs"):
            st.experimental_rerun()
        
        # Get logs
        logs = log_reader.get_all_logs(limit=50)
        
        if not logs:
            st.info("No logs found. API requests will be logged here when they are made.")
        else:
            st.success(f"Found {len(logs)} log entries")
            
            # Display logs in an expander for each log
            for i, log in enumerate(logs):
                timestamp = log.get('formatted_timestamp', 'Unknown time')
                filename = log.get('filename', 'Unknown file')
                
                # Get request info
                request = log.get('request', {})
                request_id = request.get('ICL_POST_ID', 'Unknown')
                country = request.get('Shipping_Country', 'Unknown')
                
                # Get response info
                response = log.get('response', {})
                status = response.get('status', 'No response') if isinstance(response, dict) else 'No response'
                
                # Create expander title with key info
                expander_title = f"Request {request_id} to {country} - {timestamp} - Status: {status}"
                
                with st.expander(expander_title):
                    # Create tabs within the expander
                    log_tabs = st.tabs(["Overview", "Request", "Response", "Raw JSON"])
                    
                    with log_tabs[0]:
                        # Overview tab
                        st.markdown("#### Request Overview")
                        
                        # Create columns for key details
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Request Details:**")
                            st.markdown(f"- **ID:** {request_id}")
                            st.markdown(f"- **Time:** {timestamp}")
                            st.markdown(f"- **File:** {filename}")
                            
                        with col2:
                            st.markdown("**Shipping Details:**")
                            st.markdown(f"- **Country:** {request.get('Shipping_Country', 'N/A')}")
                            st.markdown(f"- **City:** {request.get('Shipping_City', 'N/A')}")
                            st.markdown(f"- **Zip:** {request.get('Shipping_Zip', 'N/A')}")
                            st.markdown(f"- **Incoterm:** {request.get('Incoterm', 'N/A')}")
                        
                        # Display status
                        if status == 'success':
                            st.success(f"Status: {status}")
                        elif status == 'error':
                            st.error(f"Status: {status}")
                            if isinstance(response, dict) and 'message' in response:
                                st.error(f"Error: {response['message']}")
                        else:
                            st.info(f"Status: {status}")
                    
                    with log_tabs[1]:
                        # Request tab
                        st.markdown("#### Request Data")
                        
                        # Display line items
                        st.subheader("Line Items")
                        
                        # Create a table for line items
                        line_items = []
                        
                        # Check for Line_1
                        if all(k in request for k in ['Line_1_UW', 'Line_1_UH', 'Line_1_UD', 'Line_1_KG']):
                            line_items.append({
                                'Line': 1,
                                'Width (m)': request.get('Line_1_UW'),
                                'Height (m)': request.get('Line_1_UH'),
                                'Depth (m)': request.get('Line_1_UD'),
                                'Weight (kg)': request.get('Line_1_KG'),
                                'Quantity': request.get('Line_1_total_U'),
                                'Volume (m³)': request.get('Line_1_total_V'),
                                'Total Weight (kg)': request.get('Line_1_total_KG')
                            })
                        
                        # Check for Line_2
                        if all(k in request and request[k] is not None for k in ['Line_2_UW', 'Line_2_UH', 'Line_2_UD', 'Line_2_KG']):
                            line_items.append({
                                'Line': 2,
                                'Width (m)': request.get('Line_2_UW'),
                                'Height (m)': request.get('Line_2_UH'),
                                'Depth (m)': request.get('Line_2_UD'),
                                'Weight (kg)': request.get('Line_2_KG'),
                                'Quantity': request.get('Line_2_total_U'),
                                'Volume (m³)': request.get('Line_2_total_V'),
                                'Total Weight (kg)': request.get('Line_2_total_KG')
                            })
                        
                        if line_items:
                            st.dataframe(line_items)
                        else:
                            st.warning("No line items found in request")
                        
                        # Other request details
                        st.subheader("Other Details")
                        other_details = {k: v for k, v in request.items() if not k.startswith('Line_')}
                        st.json(other_details)
                    
                    with log_tabs[2]:
                        # Response tab
                        st.markdown("#### Response Data")
                        
                        if not response:
                            st.warning("No response data available")
                        elif isinstance(response, dict):
                            # Check if it's a TeldorResponse
                            if 'service_levels' in response:
                                st.subheader("Service Levels")
                                
                                # Create a table for service levels
                                if response['service_levels']:
                                    service_levels = []
                                    for sl in response['service_levels']:
                                        service_levels.append({
                                            'Service': sl.get('name', 'Unknown'),
                                            'Price': sl.get('price', 0),
                                            'Currency': sl.get('currency', 'eur').upper()
                                        })
                                    
                                    st.dataframe(service_levels)
                                else:
                                    st.warning("No service levels in response")
                                
                                # Display dimensions
                                st.subheader("Dimensions")
                                if 'dimensions' in response:
                                    dims = response['dimensions']
                                    st.markdown(f"- **Length:** {dims.get('length', 'N/A')} cm")
                                    st.markdown(f"- **Width:** {dims.get('width', 'N/A')} cm")
                                    st.markdown(f"- **Height:** {dims.get('height', 'N/A')} cm")
                                    st.markdown(f"- **Collo:** {dims.get('num_collo', 'N/A')}")
                                
                                # Display weights
                                st.subheader("Weights")
                                st.markdown(f"- **Chargeable Weight:** {response.get('chargeable_weight', 'N/A')} kg")
                                st.markdown(f"- **Combined Weight:** {response.get('combined_weight', 'N/A')} kg")
                                st.markdown(f"- **Non-stackable Weight:** {response.get('non_stackable_weight', 'N/A')} kg")
                                st.markdown(f"- **Weight Type:** {response.get('weight_type', 'N/A')}")
                                
                                # Display zone
                                st.subheader("Zone")
                                st.markdown(f"- **Zone:** {response.get('zone', 'N/A')}")
                            else:
                                # Generic response
                                st.json(response)
                        else:
                            st.text(str(response))
                    
                    with log_tabs[3]:
                        # Raw JSON tab
                        st.markdown("#### Raw Log Data")
                        st.json(log)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <p>CTS Shipping Calculator v1.0</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()