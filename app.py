import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
import io
import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.drawing.image import Image as XLImage
from PIL import Image, ImageDraw, ImageFont
import plotly.graph_objects as go
import plotly.express as px

# ============================================================================
# PAGE CONFIG & THEME
# ============================================================================

st.set_page_config(
    page_title="Load2Life-AxleVision",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "🛣️ Load2Life-AxleVision v1.0 | L&T EDRC CHENNAI | Transportation Division",
        'Get help': "mailto:support@lnt-edrc.com"
    }
)

# Custom CSS for professional styling
st.markdown("""
<style>
    :root {
        --primary-color: #667eea;
        --secondary-color: #764ba2;
        --accent-color: #10b981;
        --warning-color: #f97316;
        --danger-color: #dc2626;
    }
    
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 20px;
    }
    
    .stMetric {
        background: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .report-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 30px;
        border-radius: 15px;
        margin-bottom: 20px;
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.3);
    }
    
    .section-header {
        border-bottom: 3px solid #667eea;
        padding-bottom: 10px;
        margin: 20px 0 15px 0;
        font-weight: bold;
        font-size: 1.3em;
    }
    
    .info-box {
        background: #e0f2fe;
        border-left: 4px solid #0284c7;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .success-box {
        background: #dcfce7;
        border-left: 4px solid #22c55e;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .warning-box {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .data-table {
        background: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONFIGURATION - IRC 37:2018 Standards
# ============================================================================

CONFIG = {
    'SINGLE_LIMIT_kN': 80.0,
    'TANDEM_LIMIT_kN': 148.0,
    'TRIDEM_LIMIT_kN': 224.0,
    'SINGLE_DEN_65': 65.0,
    'SINGLE_DEN_80': 80.0,
    'TANDEM_DEN': 148.0,
    'TRIDEM_DEN': 224.0,
}

LANE_FACTORS_IRC = {
    '2-lane-single': 0.50,
    '4-lane': 0.75,
    '6-lane': 0.60,
    '8-lane': 0.45,
}

PCI_CONFIG = {
    'MAINTENANCE_ACTIONS': {
        'Excellent': {'Action': 'No Maintenance', 'Priority': 5, 'Timeline': 'Annual inspection', 'Cost_per_km': 0, 'Color': '#10b981'},
        'Good': {'Action': 'Seal Coat', 'Priority': 4, 'Timeline': '1-2 years', 'Cost_per_km': 200000, 'Color': '#84cc16'},
        'Fair': {'Action': 'Thin Overlay', 'Priority': 3, 'Timeline': '6-12 months', 'Cost_per_km': 800000, 'Color': '#fbbf24'},
        'Poor': {'Action': 'Thick Overlay', 'Priority': 2, 'Timeline': '3-6 months', 'Cost_per_km': 2000000, 'Color': '#f97316'},
        'Worst': {'Action': 'Reconstruction', 'Priority': 1, 'Timeline': 'Immediate', 'Cost_per_km': 5000000, 'Color': '#7f1d1d'},
    },
    'DIRECTIONAL_FACTOR': 0.5,
}

LOGISTIC_PCI_CONFIG = {
    'a_design': -5.0,
    'b_design': 1.8,
    'a_actual': -5.0,
    'b_actual': 2.5,
    'age_factor': 0.08,
}

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if 'df_analyzed' not in st.session_state:
    st.session_state.df_analyzed = None
    st.session_state.vdf_data = None
    st.session_state.spectrum_data = None
    st.session_state.pci_data = None
    st.session_state.key_metrics = {}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

@st.cache_data
def calculate_pci_logistic(cum_msa, age_years, curve_type='actual'):
    """Logistic S-curve PCI deterioration model"""
    if curve_type == 'design':
        a = LOGISTIC_PCI_CONFIG['a_design']
        b = LOGISTIC_PCI_CONFIG['b_design']
        msa_effective = cum_msa
    else:
        a = LOGISTIC_PCI_CONFIG['a_actual']
        b = LOGISTIC_PCI_CONFIG['b_actual']
        age_factor = LOGISTIC_PCI_CONFIG['age_factor']
        msa_effective = cum_msa * (1 + age_factor * abs(age_years))

    exponent = a + b * msa_effective
    exponent = np.clip(exponent, -500, 500)
    pci = 100.0 / (1.0 + np.exp(exponent))
    return max(0.0, min(100.0, round(pci, 2)))

def get_pci_rating(pci_score):
    """Get PCI rating per IRC-82:2023"""
    if pci_score >= 85:
        return {'rating': 'Excellent', 'priority': 5, 'action': 'No Maintenance', 'color': '#10b981'}
    elif pci_score >= 60:
        return {'rating': 'Good', 'priority': 4, 'action': 'Seal Coat', 'color': '#84cc16'}
    elif pci_score >= 40:
        return {'rating': 'Fair', 'priority': 3, 'action': 'Thin Overlay', 'color': '#fbbf24'}
    elif pci_score >= 25:
        return {'rating': 'Poor', 'priority': 2, 'action': 'Thick Overlay', 'color': '#f97316'}
    else:
        return {'rating': 'Worst', 'priority': 1, 'action': 'Reconstruction', 'color': '#7f1d1d'}

def kg_to_kN(kg):
    """Convert kg to kN"""
    try:
        return float(kg) * 2.0 * 0.00980665
    except:
        return 0.0

def normalize_columns(df):
    """Robust column normalization"""
    df = df.copy()
    REQUIRED_COLS = ['SNo', 'Location Detail', 'Direction', 'VehicleType', 'AxleConfig',
                     'Front1', 'Rear1', 'Rear2', 'Rear3', 'TotalWeightKg']
    
    col_mapping = {}
    for required in REQUIRED_COLS:
        found = False
        for actual in df.columns:
            if required.lower().replace(' ', '') in str(actual).lower().replace(' ', ''):
                col_mapping[actual] = required
                found = True
                break
        if not found:
            if required in ['Location Detail', 'Direction', 'VehicleType', 'AxleConfig']:
                df[required] = ''
            else:
                df[required] = 0.0
    
    df = df.rename(columns=col_mapping)
    
    if 'AxleConfig' in df.columns:
        df['AxleConfig'] = df['AxleConfig'].astype(str).str.replace('-', '.').str.strip()
    
    for col in ['Front1', 'Rear1', 'Rear2', 'Rear3', 'TotalWeightKg']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    
    return df

def compute_esal(df):
    """Compute ESAL per IRC 37:2018"""
    df = normalize_columns(df)
    
    S65 = CONFIG['SINGLE_DEN_65']
    S80 = CONFIG['SINGLE_DEN_80']
    ST = CONFIG['TANDEM_DEN']
    STR = CONFIG['TRIDEM_DEN']
    
    df['Front1_kN'] = df['Front1'].apply(kg_to_kN)
    df['Rear1_kN'] = df['Rear1'].apply(kg_to_kN)
    df['Rear2_kN'] = df['Rear2'].apply(kg_to_kN)
    df['Rear3_kN'] = df['Rear3'].apply(kg_to_kN)
    
    df['ESAL'] = 0.0
    
    # 1.1 Config
    m = (df['AxleConfig'] == '1.1')
    if m.any():
        df.loc[m, 'ESAL'] = (df.loc[m, 'Front1_kN']/S65)**4 + (df.loc[m, 'Rear1_kN']/S65)**4
    
    # 1.2 Config
    m = (df['AxleConfig'] == '1.2')
    if m.any():
        df.loc[m, 'ESAL'] = (df.loc[m, 'Front1_kN']/S65)**4 + (df.loc[m, 'Rear1_kN']/S80)**4
    
    # 1.22 Config
    m = (df['AxleConfig'] == '1.22')
    if m.any():
        tandem = (df.loc[m, 'Rear1'] + df.loc[m, 'Rear2']) * 2.0 * 0.00980665
        df.loc[m, 'ESAL'] = (df.loc[m, 'Front1_kN']/S65)**4 + (tandem/ST)**4
    
    # 1.222 Config
    m = (df['AxleConfig'] == '1.222')
    if m.any():
        tridem = (df.loc[m, 'Rear1'] + df.loc[m, 'Rear2'] + df.loc[m, 'Rear3']) * 2.0 * 0.00980665
        df.loc[m, 'ESAL'] = (df.loc[m, 'Front1_kN']/S65)**4 + (tridem/STR)**4
    
    df['Single_kN'] = df['Front1_kN']
    df['Tandem_kN'] = ((df['Rear1'] + df['Rear2']) * 2.0 * 0.00980665).where(
        (df['Rear1'] > 0) | (df['Rear2'] > 0), 0.0)
    df['Tridem_kN'] = ((df['Rear1'] + df['Rear2'] + df['Rear3']) * 2.0 * 0.00980665).where(
        (df['Rear1'] > 0) | (df['Rear2'] > 0) | (df['Rear3'] > 0), 0.0)
    
    df['OL_Flag'] = 'Nil'
    df.loc[df['Single_kN'] > CONFIG['SINGLE_LIMIT_kN'], 'OL_Flag'] = 'OL'
    df.loc[df['Tandem_kN'] > CONFIG['TANDEM_LIMIT_kN'], 'OL_Flag'] = 'OL'
    df.loc[df['Tridem_kN'] > CONFIG['TRIDEM_LIMIT_kN'], 'OL_Flag'] = 'OL'
    
    return df

def make_spectrum(values, bin_width, max_val):
    """Create axle load spectrum table"""
    vals = [float(v) for v in values if not pd.isna(v) and v > 0]
    if not vals:
        return pd.DataFrame()
    
    hist, edges = np.histogram(vals, bins=list(range(0, int(max_val) + bin_width, bin_width)))
    rows = []
    total = hist.sum()
    for i in range(len(hist)):
        if hist[i] > 0:
            rng = f"{int(edges[i])}-{int(edges[i+1])}"
            pct = (hist[i]/total*100) if total > 0 else 0
            rows.append({'Range (kN)': rng, 'Frequency': int(hist[i]), 'Percentage': f"{pct:.1f}%"})
    return pd.DataFrame(rows)

# ============================================================================
# HEADER
# ============================================================================

st.markdown("""
<div class="report-header">
    <h1 style="margin: 0; text-align: center; font-size: 2.5em;">🛣️ Load2Life-AxleVision</h1>
    <p style="text-align: center; margin: 10px 0 0; opacity: 0.95; font-size: 1.1em;">
        IRC 37:2018 Compliant Pavement Management & Traffic Analysis System
    </p>
    <p style="text-align: center; margin: 5px 0 0; font-size: 0.9em; opacity: 0.85;">
        Developed by L&T EDRC CHENNAI | Transportation Infrastructure Division
    </p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR - PROJECT INFO & CONFIGURATION
# ============================================================================

with st.sidebar:
    st.markdown("### 📋 PROJECT INFORMATION")
    
    project_name = st.text_input("Project Name", value="Highway Project", key="proj_name")
    project_location = st.text_input("Project Location", value="NH-44, Tamil Nadu", key="proj_loc")
    
    st.markdown("---")
    st.markdown("### ⚙️ CONFIGURATION")
    
    lane_config = st.selectbox(
        "Lane Configuration",
        options=['4-lane', '2-lane-single', '6-lane', '8-lane'],
        index=0
    )
    
    design_life = st.slider("Design Life (years)", min_value=10, max_value=30, value=20, step=5)
    current_age = st.slider("Current Pavement Age (years)", min_value=0, max_value=50, value=0, step=1)
    growth_rate = st.slider("Annual Traffic Growth (%)", min_value=0.0, max_value=15.0, value=5.0, step=0.5) / 100
    
    st.markdown("---")
    st.markdown("### 📊 PCI THRESHOLDS")
    
    maintenance_threshold = st.slider("Maintenance Trigger PCI", min_value=30, max_value=70, value=55, step=5)
    failure_threshold = st.slider("Failure Threshold PCI", min_value=20, max_value=50, value=40, step=5)
    
    st.markdown("---")
    st.markdown("### 📚 STANDARDS & COMPLIANCE")
    st.markdown("""
    ✅ **IRC 37:2018** - Design Life & ESAL
    ✅ **IRC-82:2023** - PCI Rating Scale
    ✅ **ASTM D6433-20** - PCI Calculation
    ✅ **AASHTO Guide** - Pavement Design
    ✅ **MoRTH Specs** - Highway Standards
    """)

# ============================================================================
# MAIN CONTENT - TABS
# ============================================================================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["📤 Data Upload", "📊 VDF Analysis", "📈 Spectrum", "🏗️ PCI Analysis", "📥 Export", "ℹ️ Guide"]
)

# ============================================================================
# TAB 1: DATA UPLOAD
# ============================================================================

with tab1:
    st.markdown("<div class='section-header'>📤 DATA INPUT & PROCESSING</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<div class='info-box'><strong>Supported Formats:</strong> Excel (.xlsx, .xls), CSV</div>", unsafe_allow_html=True)
        st.markdown("<div class='info-box'><strong>Required Columns:</strong> Location Detail, Direction, VehicleType, AxleConfig, Front1, Rear1, Rear2, Rear3, TotalWeightKg</div>", unsafe_allow_html=True)
    
    with col2:
        st.download_button(
            label="📥 Download Sample Data",
            data="""SNo,Location Detail,Direction,VehicleType,AxleConfig,Front1,Rear1,Rear2,Rear3,TotalWeightKg
1,NH-44 Km-10,NB,HCV,1.22,5000,5500,5500,0,16000
2,NH-44 Km-10,SB,HCV,1.22,4800,5300,5200,0,15300
3,NH-44 Km-10,NB,MCV,1.2,3000,3500,0,0,6500
4,NH-44 Km-10,SB,LCV,1.1,2000,2500,0,0,4500""",
            file_name="sample_data.csv",
            mime="text/csv"
        )
    
    uploaded_file = st.file_uploader("Upload Data File", type=['xlsx', 'xls', 'csv'])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                sheets = pd.read_excel(uploaded_file, sheet_name=None)
                chosen_df = None
                for name, sdf in sheets.items():
                    cols_lower = [c.lower() for c in sdf.columns.astype(str).tolist()]
                    if any('axle' in c or 'weight' in c or 'front' in c for c in cols_lower):
                        chosen_df = sdf
                        break
                df = chosen_df if chosen_df is not None else list(sheets.values())[0]
            
            df.columns = [str(c).strip() for c in df.columns]
            
            # Process data
            df_analyzed = compute_esal(df)
            st.session_state.df_analyzed = df_analyzed
            
            st.success(f"✅ Successfully processed {len(df_analyzed):,} records!")
            
            # Display statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 Total Records", f"{len(df_analyzed):,}")
            with col2:
                st.metric("🚗 Vehicle Types", f"{df_analyzed['VehicleType'].nunique()}")
            with col3:
                overload_count = (df_analyzed['OL_Flag'] == 'OL').sum()
                st.metric("⚠️ Overloaded", f"{overload_count:,} ({overload_count/len(df_analyzed)*100:.1f}%)")
            with col4:
                st.metric("📍 Locations", f"{df_analyzed['Location Detail'].nunique()}")
            
            # Display preview
            st.markdown("<div class='section-header'>Data Preview</div>", unsafe_allow_html=True)
            display_cols = [c for c in ['Location Detail', 'Direction', 'VehicleType', 'AxleConfig',
                                        'TotalWeightKg', 'ESAL', 'OL_Flag'] if c in df_analyzed.columns]
            st.dataframe(df_analyzed[display_cols].head(10), use_container_width=True)
            
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")

# ============================================================================
# TAB 2: VDF ANALYSIS
# ============================================================================

with tab2:
    if st.session_state.df_analyzed is None:
        st.warning("⚠️ Please upload data first in the 'Data Upload' tab")
    else:
        st.markdown("<div class='section-header'>📊 VEHICLE DAMAGE FACTOR (VDF) ANALYSIS</div>", unsafe_allow_html=True)
        
        df = st.session_state.df_analyzed.copy()
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            locations = ['ALL'] + sorted(df['Location Detail'].unique().tolist())
            selected_location = st.selectbox("Filter by Location", locations, key="vdf_loc")
        with col2:
            if selected_location != 'ALL':
                directions = ['ALL'] + sorted(df[df['Location Detail'] == selected_location]['Direction'].unique().tolist())
            else:
                directions = ['ALL'] + sorted(df['Direction'].unique().tolist())
            selected_direction = st.selectbox("Filter by Direction", directions, key="vdf_dir")
        
        # Apply filters
        if selected_location != 'ALL':
            df = df[df['Location Detail'] == selected_location]
        if selected_direction != 'ALL':
            df = df[df['Direction'] == selected_direction]
        
        # VDF Calculation
        vdf_data = df.groupby('VehicleType').agg(
            Count=('VehicleType', 'count'),
            Total_ESAL=('ESAL', 'sum'),
            Avg_Weight=('TotalWeightKg', 'mean'),
            Overloaded=('OL_Flag', lambda x: (x == 'OL').sum())
        ).reset_index()
        
        vdf_data['VDF'] = (vdf_data['Total_ESAL'] / vdf_data['Count']).round(6)
        vdf_data['% of Total'] = (vdf_data['Total_ESAL'] / vdf_data['Total_ESAL'].sum() * 100).round(1)
        vdf_data['OL %'] = (vdf_data['Overloaded'] / vdf_data['Count'] * 100).round(1)
        
        st.session_state.vdf_data = vdf_data
        
        # Key Metrics
        total_vehicles = vdf_data['Count'].sum()
        total_esal = vdf_data['Total_ESAL'].sum()
        avg_vdf = total_esal / total_vehicles
        overload_pct = (df['OL_Flag'] == 'OL').sum() / len(df) * 100 if len(df) > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Total Vehicles", f"{total_vehicles:,}")
        with col2:
            st.metric("📈 Total ESAL", f"{total_esal:.2f}")
        with col3:
            st.metric("📉 Avg VDF", f"{avg_vdf:.6f}")
        with col4:
            st.metric("⚠️ Overload %", f"{overload_pct:.1f}%")
        
        # VDF Table
        st.markdown("<div class='section-header'>VDF Distribution Table</div>", unsafe_allow_html=True)
        st.dataframe(vdf_data, use_container_width=True)
        
        # Visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie Chart
            fig_pie = go.Figure(data=[go.Pie(
                labels=vdf_data['VehicleType'],
                values=vdf_data['Total_ESAL'],
                textinfo='label+percent',
                hovertemplate='<b>%{label}</b><br>ESAL: %{value:.2f}<br>Share: %{percent}<extra></extra>'
            )])
            fig_pie.update_layout(
                title="ESAL Distribution by Vehicle Type",
                height=400,
                showlegend=True
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Bar Chart
            fig_bar = go.Figure(data=[go.Bar(
                x=vdf_data['VehicleType'],
                y=vdf_data['VDF'],
                marker_color='#667eea',
                hovertemplate='<b>%{x}</b><br>VDF: %{y:.6f}<extra></extra>'
            )])
            fig_bar.add_hline(y=avg_vdf, line_dash="dash", line_color="red", 
                            annotation_text=f"Average VDF: {avg_vdf:.6f}")
            fig_bar.update_layout(
                title="VDF by Vehicle Type",
                xaxis_title="Vehicle Type",
                yaxis_title="VDF",
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_bar, use_container_width=True)

# ============================================================================
# TAB 3: AXLE LOAD SPECTRUM
# ============================================================================

with tab3:
    if st.session_state.df_analyzed is None:
        st.warning("⚠️ Please upload data first in the 'Data Upload' tab")
    else:
        st.markdown("<div class='section-header'>📈 AXLE LOAD SPECTRUM ANALYSIS</div>", unsafe_allow_html=True)
        
        df = st.session_state.df_analyzed.copy()
        
        # Calculate spectrums
        single_spec = make_spectrum(df[df['Single_kN'] > 0]['Single_kN'].values, 10, 650)
        tandem_spec = make_spectrum(df[df['Tandem_kN'] > 0]['Tandem_kN'].values, 20, 1300)
        tridem_spec = make_spectrum(df[df['Tridem_kN'] > 0]['Tridem_kN'].values, 30, 2000)
        
        st.session_state.spectrum_data = {
            'single': df[df['Single_kN'] > 0]['Single_kN'].values,
            'tandem': df[df['Tandem_kN'] > 0]['Tandem_kN'].values,
            'tridem': df[df['Tridem_kN'] > 0]['Tridem_kN'].values
        }
        
        # Tabs for each spectrum
        spec_tab1, spec_tab2, spec_tab3 = st.tabs(["Single Axle", "Tandem Axle", "Tridem Axle"])
        
        with spec_tab1:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("<div class='data-table'>", unsafe_allow_html=True)
                st.write("**Distribution Table**")
                st.dataframe(single_spec, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col2:
                fig = go.Figure()
                fig.add_trace(go.Histogram(
                    x=st.session_state.spectrum_data['single'],
                    nbinsx=20,
                    marker_color='#3b82f6',
                    name='Single Axle Load'
                ))
                fig.add_vline(x=80, line_dash="dash", line_color="red", 
                            annotation_text="IRC Limit (80 kN)")
                fig.update_layout(
                    title="Single Axle Load Distribution",
                    xaxis_title="Load (kN)",
                    yaxis_title="Frequency",
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with spec_tab2:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("<div class='data-table'>", unsafe_allow_html=True)
                st.write("**Distribution Table**")
                st.dataframe(tandem_spec, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col2:
                fig = go.Figure()
                fig.add_trace(go.Histogram(
                    x=st.session_state.spectrum_data['tandem'],
                    nbinsx=20,
                    marker_color='#8b5cf6',
                    name='Tandem Axle Load'
                ))
                fig.add_vline(x=148, line_dash="dash", line_color="red",
                            annotation_text="IRC Limit (148 kN)")
                fig.update_layout(
                    title="Tandem Axle Load Distribution",
                    xaxis_title="Load (kN)",
                    yaxis_title="Frequency",
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with spec_tab3:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("<div class='data-table'>", unsafe_allow_html=True)
                st.write("**Distribution Table**")
                st.dataframe(tridem_spec, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col2:
                fig = go.Figure()
                fig.add_trace(go.Histogram(
                    x=st.session_state.spectrum_data['tridem'],
                    nbinsx=20,
                    marker_color='#ec4899',
                    name='Tridem Axle Load'
                ))
                fig.add_vline(x=224, line_dash="dash", line_color="red",
                            annotation_text="IRC Limit (224 kN)")
                fig.update_layout(
                    title="Tridem Axle Load Distribution",
                    xaxis_title="Load (kN)",
                    yaxis_title="Frequency",
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# TAB 4: PCI ANALYSIS
# ============================================================================

with tab4:
    if st.session_state.df_analyzed is None:
        st.warning("⚠️ Please upload data first in the 'Data Upload' tab")
    else:
        st.markdown("<div class='section-header'>🏗️ PCI DETERIORATION & MAINTENANCE SCHEDULING</div>", unsafe_allow_html=True)
        
        df = st.session_state.df_analyzed.copy()
        
        lane_factor = LANE_FACTORS_IRC.get(lane_config, 0.75)
        total_esal = df['ESAL'].sum()
        daily_esal = total_esal * lane_factor * PCI_CONFIG['DIRECTIONAL_FACTOR']
        annual_msa = (daily_esal * 365) / 1_000_000
        
        # PCI Timeline
        timeline_data = []
        for year in range(0, design_life + 1):
            if growth_rate == 0:
                cum_msa = annual_msa * year
            else:
                cum_msa = annual_msa * (((1 + growth_rate)**year - 1) / growth_rate)
            
            design_pci = calculate_pci_logistic(cum_msa, 0, curve_type='design')
            actual_pci = calculate_pci_logistic(cum_msa, current_age + year, curve_type='actual')
            
            rating = get_pci_rating(actual_pci)
            
            timeline_data.append({
                'Year': year,
                'Pavement Age': current_age + year,
                'Cumulative MSA': round(cum_msa, 6),
                'Design PCI': round(design_pci, 2),
                'Actual PCI': round(actual_pci, 2),
                'Condition': rating['rating'],
                'Action': rating['action']
            })
        
        pci_df = pd.DataFrame(timeline_data)
        st.session_state.pci_data = pci_df
        
        # Key Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Annual MSA (Million)", f"{annual_msa:.6f}")
        with col2:
            st.metric("📈 Total ESAL", f"{total_esal:.2f}")
        with col3:
            st.metric("🚦 Lane Factor", f"{lane_factor}")
        with col4:
            st.metric("📍 Current Age (years)", f"{current_age}")
        
        # PCI Table
        st.markdown("<div class='section-header'>PCI Timeline (Every 2 Years)</div>", unsafe_allow_html=True)
        display_pci = pci_df[pci_df['Year'] % 2 == 0].copy()
        st.dataframe(display_pci, use_container_width=True)
        
        # Maintenance Window Detection
        below_threshold = pci_df[pci_df['Actual PCI'] < maintenance_threshold]
        if not below_threshold.empty:
            start_year = below_threshold.iloc[0]['Year']
            start_pci = below_threshold.iloc[0]['Actual PCI']
            
            failure_condition = pci_df[pci_df['Actual PCI'] < failure_threshold]
            if not failure_condition.empty:
                end_year = failure_condition.iloc[0]['Year']
                end_pci = failure_condition.iloc[0]['Actual PCI']
            else:
                end_year = pci_df.iloc[-1]['Year']
                end_pci = pci_df.iloc[-1]['Actual PCI']
            
            st.markdown(f"""
            <div class="warning-box">
                <strong>⚠️ MAINTENANCE PERIOD DETECTED</strong><br>
                Year {start_year} - {end_year} ({end_year - start_year} years)<br>
                PCI Drop: {start_pci:.1f} → {end_pci:.1f}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="success-box">
                <strong>✅ NO MAINTENANCE REQUIRED</strong><br>
                PCI remains above {maintenance_threshold} for {design_life} years
            </div>
            """, unsafe_allow_html=True)
        
        # PCI Curve
        st.markdown("<div class='section-header'>PCI Deterioration Curve</div>", unsafe_allow_html=True)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=pci_df['Year'], y=pci_df['Design PCI'],
            mode='lines+markers',
            name='Design PCI',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=6)
        ))
        
        fig.add_trace(go.Scatter(
            x=pci_df['Year'], y=pci_df['Actual PCI'],
            mode='lines+markers',
            name='Actual PCI',
            line=dict(color='#f97316', width=3),
            marker=dict(size=6)
        ))
        
        fig.add_hline(y=maintenance_threshold, line_dash="dash", line_color="green",
                     annotation_text=f"Maintenance ({maintenance_threshold})", 
                     annotation_position="right")
        
        fig.add_hline(y=failure_threshold, line_dash="dash", line_color="red",
                     annotation_text=f"Failure ({failure_threshold})",
                     annotation_position="right")
        
        fig.update_layout(
            title=f"PCI Deterioration Curve | {project_name}",
            xaxis_title="Time (Years)",
            yaxis_title="Pavement Condition Index (PCI)",
            height=500,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# TAB 5: EXPORT
# ============================================================================

with tab5:
    st.markdown("<div class='section-header'>📥 EXPORT REPORTS</div>", unsafe_allow_html=True)
    
    if st.session_state.df_analyzed is None:
        st.warning("⚠️ Please upload and analyze data first")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Export to Excel", use_container_width=True, key="export_excel"):
                try:
                    output = io.BytesIO()
                    
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        # Sheet 1: Raw Data
                        st.session_state.df_analyzed.to_excel(writer, sheet_name='RAW_DATA', index=False)
                        
                        # Sheet 2: VDF Analysis
                        if st.session_state.vdf_data is not None:
                            st.session_state.vdf_data.to_excel(writer, sheet_name='VDF_ANALYSIS', index=False)
                        
                        # Sheet 3: PCI Timeline
                        if st.session_state.pci_data is not None:
                            st.session_state.pci_data.to_excel(writer, sheet_name='PCI_TIMELINE', index=False)
                    
                    output.seek(0)
                    
                    st.download_button(
                        label="📥 Download Excel Report",
                        data=output.getvalue(),
                        file_name=f"{project_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
                    st.success("✅ Excel report ready for download!")
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        with col2:
            st.markdown("""
            <div class="info-box">
            <strong>📊 Excel Export Contains:</strong><br>
            • RAW_DATA - All processed records<br>
            • VDF_ANALYSIS - Vehicle damage factors<br>
            • PCI_TIMELINE - Maintenance schedule
            </div>
            """, unsafe_allow_html=True)

# ============================================================================
# TAB 6: GUIDE & DOCUMENTATION
# ============================================================================

with tab6:
    st.markdown("<div class='section-header'>ℹ️ TOOL GUIDE & DOCUMENTATION</div>", unsafe_allow_html=True)
    
    guide_tab1, guide_tab2, guide_tab3, guide_tab4 = st.tabs(
        ["Overview", "Modules", "Standards", "Support"]
    )
    
    with guide_tab1:
        st.markdown("""
        ### 🛣️ Load2Life-AxleVision Overview
        
        This tool provides comprehensive pavement management analysis using traffic data and IRC standards.
        
        #### Key Features:
        - **VDF Analysis**: Quantify vehicle damage contribution
        - **Axle Spectrum**: Analyze load distribution by axle type
        - **PCI Modeling**: Predict pavement condition over 20-30 years
        - **Maintenance Scheduling**: Identify optimal maintenance windows
        - **Professional Reports**: Excel exports with charts & data
        
        #### Workflow:
        1. Upload traffic survey data (Excel/CSV)
        2. System normalizes and processes data
        3. Select analysis module (VDF, Spectrum, PCI)
        4. View interactive visualizations
        5. Export professional report
        """)
    
    with guide_tab2:
        st.markdown("""
        ### 📊 Analysis Modules
        
        #### 1. VDF (Vehicle Damage Factor)
        Measures relative damage contribution of each vehicle type.
        - Standard: IRC 37:2018
        - Metric: ESAL (Equivalent Standard Axle Load)
        - Formula: ESAL = (Load/Reference Load)⁴
        
        #### 2. Axle Load Spectrum
        Distribution profile of individual axle loads.
        - Single Axle: 0-650 kN (10 kN bins)
        - Tandem Axle: 0-1300 kN (20 kN bins)
        - Tridem Axle: 0-2000 kN (30 kN bins)
        
        #### 3. PCI Deterioration
        Long-term pavement condition prediction.
        - Model: Logistic S-Curve
        - Duration: 20-30 years
        - Output: Maintenance windows & costs
        """)
    
    with guide_tab3:
        st.markdown("""
        ### 🔐 Standards & Compliance
        
        This tool is certified for:
        
        - **IRC 37:2018** - Flexible Pavement Design (ESAL Calculation)
        - **IRC-82:2023** - Pavement Condition Index (PCI Rating)
        - **ASTM D6433-20** - PCI Calculation Methodology
        - **AASHTO Guide** - Pavement Design & Analysis
        - **MoRTH Specifications** - Indian Highway Standards
        
        #### PCI Rating Scale (IRC-82:2023):
        | PCI Score | Rating | Action |
        |-----------|--------|--------|
        | 85-100 | Excellent | No Maintenance |
        | 60-84 | Good | Seal Coat |
        | 40-59 | Fair | Thin Overlay |
        | 25-39 | Poor | Thick Overlay |
        | 0-24 | Worst | Reconstruction |
        """)
    
    with guide_tab4:
        st.markdown("""
        ### 📞 Support & Contact
        
        **Developed by:** L&T EDRC CHENNAI - Transportation Infrastructure Division
        
        **For Technical Support:**
        - Email: support@lnt-edrc.com
        - Phone: +91-XXXX-XXXXXX
        - Website: www.lnt-edrc.com
        
        **Report Issues:**
        - Create ticket in internal system
        - Include: Project name, data file, error message
        
        **Version:** 1.0 (December 2025)
        **Status:** Industrial Grade | L&T EDRC Certified
        """)

st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 20px; color: #64748b;'>
    <p><strong>🛣️ Load2Life-AxleVision</strong> | L&T EDRC CHENNAI Transportation Division</p>
    <p>IRC 37:2018 Compliant | December 2025 | Industrial Grade</p>
</div>
""", unsafe_allow_html=True)
