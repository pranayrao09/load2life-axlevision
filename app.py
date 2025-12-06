import io
import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, FancyBboxPatch
from PIL import Image, ImageDraw, ImageFont
import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.drawing.image import Image as XLImage

import streamlit as st

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Load2Life-AxleVision",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# THEME / CSS (neutral dark)
# ============================================================================

st.markdown(
    """
<style>
    :root {
        --primary-color: #4f46e5;
        --secondary-color: #7c3aed;
        --accent-color: #10b981;
        --warning-color: #f97316;
        --danger-color: #dc2626;
    }

    .main {
        background: #111827;
        padding: 20px;
        color: #e5e7eb;
    }

    body {
        background-color: #020617;
    }

    .stMarkdown, .stText, .stDataFrame {
        color: #e5e7eb !important;
    }

    .stMetric {
        background: #020617;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #4f46e5;
        box-shadow: 0 2px 10px rgba(0,0,0,0.7);
        color: #f9fafb !important;
    }
    .stMetric > div {
        color: #f9fafb !important;
    }

    .report-header {
        background: linear-gradient(135deg, #1f2937 0%, #4f46e5 45%, #7c3aed 80%);
        color: #f9fafb;
        padding: 26px 30px;
        border-radius: 14px;
        margin-bottom: 18px;
        box-shadow: 0 18px 40px rgba(0,0,0,0.8);
    }
    .report-header h1 {
        color: #f9fafb;
    }
    .report-header p {
        color: #e5e7eb;
        opacity: 0.9;
    }

    .section-header {
        border-bottom: 2px solid #4f46e5;
        padding-bottom: 8px;
        margin: 18px 0 12px 0;
        font-weight: 600;
        font-size: 1.2em;
        color: #e5e7eb;
    }

    .info-box {
        background: #020617;
        border-left: 3px solid #3b82f6;
        padding: 12px 14px;
        border-radius: 8px;
        margin: 8px 0;
        color: #e5e7eb;
        box-shadow: 0 1px 4px rgba(0,0,0,0.6);
    }

    .success-box {
        background: #022c22;
        border-left: 3px solid #22c55e;
        padding: 12px 14px;
        border-radius: 8px;
        margin: 8px 0;
        color: #bbf7d0;
    }

    .warning-box {
        background: #451a03;
        border-left: 3px solid #f97316;
        padding: 12px 14px;
        border-radius: 8px;
        margin: 8px 0;
        color: #fed7aa;
    }

    .data-table {
        background: #020617;
        border-radius: 10px;
        padding: 12px 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.75);
        color: #e5e7eb;
    }

    section[data-testid="stSidebar"] {
        background: #020617;
        color: #e5e7eb;
    }
    section[data-testid="stSidebar"] * {
        color: #e5e7eb !important;
    }

    button[data-baseweb="tab"] > div {
        color: #e5e7eb !important;
    }
    button[kind="secondary"] {
        background-color: #1f2937 !important;
        color: #e5e7eb !important;
        border-color: #374151 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================================
# CONFIGURATION
# ============================================================================

TITLE = "🛣️ Load2Life-AxleVision"

CONFIG = {
    "SINGLE_LIMIT_kN": 80.0,
    "TANDEM_LIMIT_kN": 148.0,
    "TRIDEM_LIMIT_kN": 224.0,
    "SINGLE_DEN_65": 65.0,
    "SINGLE_DEN_80": 80.0,
    "TANDEM_DEN": 148.0,
    "TRIDEM_DEN": 224.0,
    "SINGLE_BIN": 10,
    "SINGLE_MAX": 650,
    "TANDEM_BIN": 20,
    "TANDEM_MAX": 1300,
    "TRIDEM_BIN": 30,
    "TRIDEM_MAX": 2000,
}

LANE_FACTORS_IRC = {
    "2-lane-single": 0.50,
    "4-lane": 0.75,
    "6-lane": 0.60,
    "8-lane": 0.45,
}

PCI_CONFIG = {
    "MAINTENANCE_ACTIONS": {
        "Excellent": {
            "Action": "No Maintenance",
            "Priority": 5,
            "Timeline": "Annual inspection",
            "Cost_per_km": 0,
        },
        "Good": {
            "Action": "Seal Coat",
            "Priority": 4,
            "Timeline": "1-2 years",
            "Cost_per_km": 200000,
        },
        "Fair": {
            "Action": "Thin Overlay",
            "Priority": 3,
            "Timeline": "6-12 months",
            "Cost_per_km": 800000,
        },
        "Poor": {
            "Action": "Thick Overlay",
            "Priority": 2,
            "Timeline": "3-6 months",
            "Cost_per_km": 2000000,
        },
        "Worst": {
            "Action": "Reconstruction",
            "Priority": 1,
            "Timeline": "Immediate",
            "Cost_per_km": 5000000,
        },
    },
    "DIRECTIONAL_FACTOR": 0.5,
}

LOGISTIC_PCI_CONFIG = {
    "a_design": -5.0,
    "b_design": 1.8,
    "a_actual": -5.0,
    "b_actual": 2.5,
    "age_factor": 0.08,
}

REQUIRED_COLS = [
    "SNo",
    "Location Detail",
    "Direction",
    "VehicleType",
    "AxleConfig",
    "Front1",
    "Rear1",
    "Rear2",
    "Rear3",
    "TotalWeightKg",
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def calculate_pci_logistic(cum_msa, age_years, curve_type="actual"):
    if curve_type == "design":
        a = LOGISTIC_PCI_CONFIG["a_design"]
        b = LOGISTIC_PCI_CONFIG["b_design"]
        msa_effective = cum_msa
    else:
        a = LOGISTIC_PCI_CONFIG["a_actual"]
        b = LOGISTIC_PCI_CONFIG["b_actual"]
        age_factor = LOGISTIC_PCI_CONFIG["age_factor"]
        msa_effective = cum_msa * (1 + age_factor * abs(age_years))

    exponent = a + b * msa_effective
    exponent = np.clip(exponent, -500, 500)
    pci = 100.0 / (1.0 + np.exp(exponent))
    return max(0.0, min(100.0, round(pci, 2)))


def get_pci_rating(pci_score):
    if pci_score >= 85:
        return {
            "rating": "Excellent",
            "priority": 5,
            "action": "No Maintenance",
            "color": "#10b981",
        }
    elif pci_score >= 60:
        return {
            "rating": "Good",
            "priority": 4,
            "action": "Seal Coat",
            "color": "#84cc16",
        }
    elif pci_score >= 40:
        return {
            "rating": "Fair",
            "priority": 3,
            "action": "Thin Overlay",
            "color": "#fbbf24",
        }
    elif pci_score >= 25:
        return {
            "rating": "Poor",
            "priority": 2,
            "action": "Thick Overlay",
            "color": "#f97316",
        }
    else:
        return {
            "rating": "Worst",
            "priority": 1,
            "action": "Reconstruction",
            "color": "#7f1d1d",
        }


def detect_maintenance_period(pci_df, maintenance_threshold=55.0, failure_threshold=40.0):
    below_threshold = pci_df[pci_df["Actual PCI"] < maintenance_threshold]
    if below_threshold.empty:
        return None

    start_year = below_threshold.iloc[0]["Year"]
    start_pci = below_threshold.iloc[0]["Actual PCI"]

    failure_condition = pci_df[pci_df["Actual PCI"] < failure_threshold]
    if not failure_condition.empty:
        end_year = failure_condition.iloc[0]["Year"]
        end_pci = failure_condition.iloc[0]["Actual PCI"]
    else:
        end_year = pci_df.iloc[-1]["Year"]
        end_pci = pci_df.iloc[-1]["Actual PCI"]

    return {
        "start_year": start_year,
        "end_year": end_year,
        "duration": end_year - start_year,
        "start_pci": round(start_pci, 1),
        "end_pci": round(end_pci, 1),
    }


def kg_to_kN(kg):
    try:
        return float(kg) * 2.0 * 0.00980665
    except Exception:
        return 0.0


def normalize_columns(df):
    df = df.copy()
    col_mapping = {}
    for required in REQUIRED_COLS:
        found = False
        for actual in df.columns:
            if required.lower().replace(" ", "") in str(actual).lower().replace(" ", ""):
                col_mapping[actual] = required
                found = True
                break
        if not found:
            if required in ["Location Detail", "Direction", "VehicleType", "AxleConfig"]:
                df[required] = ""
            else:
                df[required] = 0.0

    df = df.rename(columns=col_mapping)

    if "AxleConfig" in df.columns:
        df["AxleConfig"] = df["AxleConfig"].astype(str).str.replace("-", ".").str.strip()

    for col in ["Front1", "Rear1", "Rear2", "Rear3", "TotalWeightKg"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    return df


def compute_esal(df):
    df = normalize_columns(df)

    S65 = CONFIG["SINGLE_DEN_65"]
    S80 = CONFIG["SINGLE_DEN_80"]
    ST = CONFIG["TANDEM_DEN"]
    STR = CONFIG["TRIDEM_DEN"]

    df["Front1_kN"] = df["Front1"].apply(kg_to_kN)
    df["Rear1_kN"] = df["Rear1"].apply(kg_to_kN)
    df["Rear2_kN"] = df["Rear2"].apply(kg_to_kN)
    df["Rear3_kN"] = df["Rear3"].apply(kg_to_kN)

    df["ESAL"] = 0.0

    m = df["AxleConfig"] == "1.1"
    if m.any():
        a = df.loc[m, "Front1_kN"]
        b = df.loc[m, "Rear1_kN"]
        df.loc[m, "ESAL"] = (a / S65) ** 4 + (b / S65) ** 4

    m = df["AxleConfig"] == "1.2"
    if m.any():
        a = df.loc[m, "Front1_kN"]
        b = df.loc[m, "Rear1_kN"]
        df.loc[m, "ESAL"] = (a / S65) ** 4 + (b / S80) ** 4

    m = df["AxleConfig"] == "1.22"
    if m.any():
        a = df.loc[m, "Front1_kN"]
        tandem = (df.loc[m, "Rear1"] + df.loc[m, "Rear2"]) * 2.0 * 0.00980665
        df.loc[m, "ESAL"] = (a / S65) ** 4 + (tandem / ST) ** 4

    m = df["AxleConfig"] == "1.222"
    if m.any():
        a = df.loc[m, "Front1_kN"]
        tridem = (
            df.loc[m, "Rear1"] + df.loc[m, "Rear2"] + df.loc[m, "Rear3"]
        ) * 2.0 * 0.00980665
        df.loc[m, "ESAL"] = (a / S65) ** 4 + (tridem / STR) ** 4

    df["Single_kN"] = df["Front1_kN"]
    df["Tandem_kN"] = (
        (df["Rear1"] + df["Rear2"]) * 2.0 * 0.00980665
    ).where((df["Rear1"] > 0) | (df["Rear2"] > 0), 0.0)
    df["Tridem_kN"] = (
        (df["Rear1"] + df["Rear2"] + df["Rear3"]) * 2.0 * 0.00980665
    ).where((df["Rear1"] > 0) | (df["Rear2"] > 0) | (df["Rear3"] > 0), 0.0)

    df["OL_Flag"] = "Nil"
    df.loc[df["Single_kN"] > CONFIG["SINGLE_LIMIT_kN"], "OL_Flag"] = "OL"
    df.loc[df["Tandem_kN"] > CONFIG["TANDEM_LIMIT_kN"], "OL_Flag"] = "OL"
    df.loc[df["Tridem_kN"] > CONFIG["TRIDEM_LIMIT_kN"], "OL_Flag"] = "OL"

    return df


def make_spectrum(values, bin_width, max_val):
    vals = [float(v) for v in values if not pd.isna(v) and v > 0]
    if not vals:
        return pd.DataFrame()

    hist, edges = np.histogram(
        vals, bins=list(range(0, int(max_val) + bin_width, bin_width))
    )
    rows = []
    total = hist.sum()
    for i in range(len(hist)):
        if hist[i] > 0:
            rng = f"{int(edges[i])}-{int(edges[i+1])}"
            pct = (hist[i] / total * 100) if total > 0 else 0
            rows.append(
                {
                    "Range (kN)": rng,
                    "Frequency": int(hist[i]),
                    "Percentage": f"{pct:.1f}%",
                }
            )
    return pd.DataFrame(rows)


def build_pdf_report(project_name, project_location):
    """Generate PDF report and return BytesIO."""
    if (
        st.session_state.df_analyzed is None
        or st.session_state.vdf_table is None
        or st.session_state.pci_timeline is None
    ):
        return None

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        df = st.session_state.df_analyzed
        vdf = st.session_state.vdf_table
        pci_df = st.session_state.pci_timeline

        # Page 1: title + overview
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")
        ax.set_title(
            f"Load2Life-AxleVision\n{project_name}",
            fontsize=18,
            weight="bold",
            pad=20,
        )
        text_lines = [
            f"Project Location: {project_location}",
            "",
            f"Total records: {len(df):,}",
            f"Vehicle types: {df['VehicleType'].nunique()}",
            f"Locations: {df['Location Detail'].nunique()}",
            f"Overloaded vehicles: {(df['OL_Flag']=='OL').sum():,}",
        ]
        ax.text(0.03, 0.8, "\n".join(text_lines), fontsize=11, va="top")
        pdf.savefig(fig)
        plt.close(fig)

        # Page 2: VDF charts
        fig, axes = plt.subplots(1, 2, figsize=(11.69, 8.27))
        colors = plt.cm.Set3(range(len(vdf)))
        axes[0].pie(
            vdf["Sum_ESAL"],
            labels=vdf["VehicleType"],
            autopct="%1.1f%%",
            colors=colors,
            startangle=140,
        )
        axes[0].set_title("ESAL Distribution by Vehicle Type")
        axes[1].barh(vdf["VehicleType"], vdf["VDF"], color=colors)
        axes[1].set_xlabel("VDF")
        axes[1].set_title("VDF by Vehicle Type")
        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # Page 3: PCI curve
        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.plot(pci_df["Year"], pci_df["Design PCI"], "-o", label="Design PCI")
        ax.plot(pci_df["Year"], pci_df["Actual PCI"], "-o", label="Actual PCI")
        ax.set_xlabel("Year")
        ax.set_ylabel("PCI")
        ax.set_title("PCI Deterioration")
        ax.grid(alpha=0.3)
        ax.legend()
        pdf.savefig(fig)
        plt.close(fig)

        # Page 4: PCI table (every 2nd year)
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")
        subset = pci_df[pci_df["Year"] % 2 == 0][
            ["Year", "Pavement Age", "Cumulative MSA", "Design PCI", "Actual PCI", "Condition"]
        ]
        ax.table(
            cellText=subset.values,
            colLabels=subset.columns,
            loc="center",
            cellLoc="center",
        )
        ax.set_title("PCI Timeline (Every 2 Years)", fontsize=14, pad=20)
        pdf.savefig(fig)
        plt.close(fig)

    buf.seek(0)
    return buf


# ============================================================================
# SESSION STATE
# ============================================================================

if "df_raw" not in st.session_state:
    st.session_state.df_raw = None
    st.session_state.df_analyzed = None
    st.session_state.vdf_table = None
    st.session_state.spectrum_tables = None
    st.session_state.pci_timeline = None
    st.session_state.key_metrics = {}
    st.session_state.selected_location = "ALL"
    st.session_state.selected_direction = "ALL"

# ============================================================================
# HEADER
# ============================================================================

st.markdown(
    f"""
<div class="report-header">
    <h1 style="margin: 0; text-align: center; font-size: 2.6em;">{TITLE}</h1>
    <p style="text-align: center; margin: 10px 0 0; font-size: 0.9em;">
        Axle Load Analysis & Pavement Management System
    </p>
    <p style="text-align: center; margin: 5px 0 0; font-size: 1.05em;">
        An Inhouse Product developed by L&T EDRC CHENNAI | Transportation Infrastructure
    </p>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================================================
# SIDEBAR (includes global filters)
# ============================================================================

with st.sidebar:
    st.markdown("### 📋 PROJECT INFO")
    project_name = st.text_input("Project Name", "Highway Project")
    project_location = st.text_input("Project Location", "NH-44, Tamil Nadu")

    st.markdown("---")
    st.markdown("### 📍 Filters")

    if st.session_state.df_analyzed is not None:
        base_df = st.session_state.df_analyzed
        loc_options = ["ALL"] + sorted(
            base_df["Location Detail"].dropna().astype(str).unique().tolist()
        )
        st.session_state.selected_location = st.selectbox(
            "Location",
            loc_options,
            index=0 if st.session_state.selected_location not in loc_options
            else loc_options.index(st.session_state.selected_location),
        )

        if st.session_state.selected_location != "ALL":
            dir_df = base_df[
                base_df["Location Detail"].astype(str)
                == st.session_state.selected_location
            ]
        else:
            dir_df = base_df

        dir_options = ["ALL"] + sorted(
            dir_df["Direction"].dropna().astype(str).unique().tolist()
        )
        st.session_state.selected_direction = st.selectbox(
            "Direction",
            dir_options,
            index=0 if st.session_state.selected_direction not in dir_options
            else dir_options.index(st.session_state.selected_direction),
        )
    else:
        st.info("Upload data to enable Location/Direction filters.")
    st.markdown("### ⚙️ CONFIGURATION")

    lane_config = st.selectbox(
        "Lane Configuration",
        options=["4-lane", "2-lane-single", "6-lane", "8-lane"],
        index=0,
    )
    design_life = st.selectbox("Design Life (years)", [10, 15, 20, 25, 30], index=2)
    current_age = st.number_input("Current Pavement Age (years)", 0, 50, 0, 1)
    growth_rate = st.slider(
        "Annual Traffic Growth (%)", min_value=0.0, max_value=15.0, value=5.0, step=0.5
    ) / 100.0

    st.markdown("### PCI THRESHOLDS")
    maintenance_threshold = st.slider(
        "Maintenance Trigger PCI", 30, 70, 55, step=5
    )
    failure_threshold = st.slider("Failure Threshold PCI", 20, 50, 40, step=5)


# ============================================================================
# FILTERED DF HELPER
# ============================================================================

def get_filtered_df():
    df = st.session_state.df_analyzed
    if df is None:
        return None, "ALL", "ALL"

    loc = st.session_state.get("selected_location", "ALL")
    drn = st.session_state.get("selected_direction", "ALL")

    if loc != "ALL":
        df = df[df["Location Detail"].astype(str) == str(loc)]
    if drn != "ALL":
        df = df[df["Direction"].astype(str) == str(drn)]

    return df.copy(), loc, drn


# ============================================================================
# TABS
# ============================================================================

tab_data, tab_vdf, tab_spectrum, tab_pci, tab_export = st.tabs(
    ["📤 Data Upload", "📊 VDF", "📈 Spectrum", "🏗️ PCI", "📥 Export"]
)

# ============================================================================
# TAB: DATA UPLOAD
# ============================================================================

with tab_data:
    st.markdown(
        "<div class='section-header'>📤 DATA INPUT & PROCESSING</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            "<div class='info-box'><strong>Supported Formats:</strong> Excel (.xlsx, .xls), CSV</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='info-box'><strong>Required Columns:</strong> Location Detail, Direction, VehicleType, AxleConfig, Front1, Rear1, Rear2, Rear3, TotalWeightKg</div>",
            unsafe_allow_html=True,
        )

    with col2:
        st.download_button(
            "📥 Download Sample Data",
            data="""SNo,Location Detail,Direction,VehicleType,AxleConfig,Front1,Rear1,Rear2,Rear3,TotalWeightKg
1,NH-44 Km-10,NB,HCV,1.22,5000,5500,5500,0,16000
2,NH-44 Km-10,SB,HCV,1.22,4800,5300,5200,0,15300
3,NH-44 Km-10,NB,MCV,1.2,3000,3500,0,0,6500
4,NH-44 Km-10,SB,LCV,1.1,2000,2500,0,0,4500
""",
            file_name="sample_data.csv",
            mime="text/csv",
        )

    uploaded = st.file_uploader("Upload Data File", type=["xlsx", "xls", "csv"])

    if uploaded is not None:
        try:
            if uploaded.size == 0:
                st.error("Uploaded file is empty.")
                st.stop()

            if uploaded.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                sheets = pd.read_excel(uploaded, sheet_name=None, engine="openpyxl")
                if not sheets:
                    st.error("No sheets found in Excel file.")
                    st.stop()
                chosen_df = None
                for name, sdf in sheets.items():
                    cols_lower = [str(c).lower() for c in sdf.columns]
                    if any("axle" in c or "weight" in c or "front" in c for c in cols_lower):
                        chosen_df = sdf
                        break
                if chosen_df is None:
                    chosen_df = list(sheets.values())[0]
                df = chosen_df

            df.columns = [str(c).strip() for c in df.columns]
            st.session_state.df_raw = df.copy()
            df_analyzed = compute_esal(df)
            st.session_state.df_analyzed = df_analyzed

            st.success(f"✅ Successfully processed {len(df_analyzed):,} records!")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Total Records", f"{len(df_analyzed):,}")
            with col2:
                st.metric("🚗 Vehicle Types", f"{df_analyzed['VehicleType'].nunique()}")
            with col3:
                overload_count = (df_analyzed["OL_Flag"] == "OL").sum()
                pct = overload_count / len(df_analyzed) * 100 if len(df_analyzed) > 0 else 0
                st.metric("⚠️ Overloaded", f"{overload_count:,} ({pct:.1f}%)")
            with col4:
                st.metric("📍 Locations", f"{df_analyzed['Location Detail'].nunique()}")

            st.markdown(
                "<div class='section-header'>Data Preview</div>",
                unsafe_allow_html=True,
            )
            display_cols = [
                c
                for c in [
                    "Location Detail",
                    "Direction",
                    "VehicleType",
                    "AxleConfig",
                    "TotalWeightKg",
                    "ESAL",
                    "OL_Flag",
                ]
                if c in df_analyzed.columns
            ]
            st.dataframe(df_analyzed[display_cols].head(10), use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error processing file: {e}")

# ============================================================================
# TAB: VDF
# ============================================================================

with tab_vdf:
    if st.session_state.df_analyzed is None:
        st.warning("⚠️ Please upload data first in the 'Data Upload' tab")
    else:
        st.markdown(
            "<div class='section-header'>📊 VEHICLE DAMAGE FACTOR (VDF) ANALYSIS</div>",
            unsafe_allow_html=True,
        )

        df, loc, drn = get_filtered_df()
        if df is None or df.empty:
            st.warning("No data after applying filters.")
        else:
            vdf = (
                df.groupby("VehicleType")
                .agg(
                    Sum_ESAL=("ESAL", "sum"),
                    Count=("VehicleType", "count"),
                    Avg_Weight=("TotalWeightKg", "mean"),
                    Overloaded=("OL_Flag", lambda x: (x == "OL").sum()),
                )
                .reset_index()
            )
            vdf["VDF"] = (vdf["Sum_ESAL"] / vdf["Count"]).round(6)
            vdf["% of Total"] = (vdf["Sum_ESAL"] / vdf["Sum_ESAL"].sum() * 100).round(1)
            vdf["OL %"] = (vdf["Overloaded"] / vdf["Count"] * 100).round(1)

            st.session_state.vdf_table = vdf

            total_esal = vdf["Sum_ESAL"].sum()
            total_veh = vdf["Count"].sum()
            avg_vdf = total_esal / total_veh if total_veh > 0 else 0
            overload_pct = (
                (df["OL_Flag"] == "OL").sum() / len(df) * 100 if len(df) > 0 else 0
            )

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Total Vehicles", f"{total_veh:,}")
            with col2:
                st.metric("📈 Total ESAL", f"{total_esal:.2f}")
            with col3:
                st.metric("📉 Avg VDF", f"{avg_vdf:.6f}")
            with col4:
                st.metric("⚠️ Overload %", f"{overload_pct:.1f}%")

            st.markdown(
                "<div class='section-header'>VDF Distribution Table</div>",
                unsafe_allow_html=True,
            )
            st.dataframe(vdf, use_container_width=True)

            fig, axes = plt.subplots(1, 2, figsize=(12, 5))
            colors = plt.cm.Set3(range(len(vdf)))

            axes[0].pie(
                vdf["Sum_ESAL"],
                labels=vdf["VehicleType"],
                autopct="%1.1f%%",
                colors=colors,
                startangle=140,
            )
            axes[0].set_title("ESAL Distribution by Vehicle Type")
            axes[1].barh(vdf["VehicleType"], vdf["VDF"], color=colors)
            axes[1].set_xlabel("VDF")
            axes[1].set_title(f"VDF by Vehicle Type (Avg: {avg_vdf:.4f})")
            plt.tight_layout()
            st.pyplot(fig)

# ============================================================================
# TAB: SPECTRUM
# ============================================================================

with tab_spectrum:
    if st.session_state.df_analyzed is None:
        st.warning("⚠️ Please upload data first in the 'Data Upload' tab")
    else:
        st.markdown(
            "<div class='section-header'>📈 AXLE LOAD SPECTRUM</div>",
            unsafe_allow_html=True,
        )

        df, loc, drn = get_filtered_df()
        if df is None or df.empty:
            st.warning("No data after applying filters.")
        else:
            single_spec = make_spectrum(
                df[df["Single_kN"] > 0]["Single_kN"].values,
                CONFIG["SINGLE_BIN"],
                CONFIG["SINGLE_MAX"],
            )
            tandem_spec = make_spectrum(
                df[df["Tandem_kN"] > 0]["Tandem_kN"].values,
                CONFIG["TANDEM_BIN"],
                CONFIG["TANDEM_MAX"],
            )
            tridem_spec = make_spectrum(
                df[df["Tridem_kN"] > 0]["Tridem_kN"].values,
                CONFIG["TRIDEM_BIN"],
                CONFIG["TRIDEM_MAX"],
            )

            st.session_state.spectrum_tables = {
                "single": single_spec,
                "tandem": tandem_spec,
                "tridem": tridem_spec,
            }

            st.subheader("Distribution Tables")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write("Single Axle")
                st.dataframe(single_spec, use_container_width=True)
            with c2:
                st.write("Tandem Axle")
                st.dataframe(tandem_spec, use_container_width=True)
            with c3:
                st.write("Tridem Axle")
                st.dataframe(tridem_spec, use_container_width=True)

            fig, axes = plt.subplots(1, 3, figsize=(15, 4))

            axes[0].hist(
                df[df["Single_kN"] > 0]["Single_kN"].values,
                bins=20,
                color="#3b82f6",
                edgecolor="black",
                alpha=0.7,
            )
            axes[0].set_title("Single Axle")
            axes[0].grid(alpha=0.3)

            axes[1].hist(
                df[df["Tandem_kN"] > 0]["Tandem_kN"].values,
                bins=20,
                color="#8b5cf6",
                edgecolor="black",
                alpha=0.7,
            )
            axes[1].set_title("Tandem Axle")
            axes[1].grid(alpha=0.3)

            axes[2].hist(
                df[df["Tridem_kN"] > 0]["Tridem_kN"].values,
                bins=20,
                color="#ec4899",
                edgecolor="black",
                alpha=0.7,
            )
            axes[2].set_title("Tridem Axle")
            axes[2].grid(alpha=0.3)

            plt.tight_layout()
            st.pyplot(fig)

# ============================================================================
# TAB: PCI
# ============================================================================

with tab_pci:
    if st.session_state.df_analyzed is None:
        st.warning("⚠️ Please upload data first in the 'Data Upload' tab")
    else:
        st.markdown(
            "<div class='section-header'>🏗️ PCI ANALYSIS</div>",
            unsafe_allow_html=True,
        )

        df, loc, drn = get_filtered_df()
        if df is None or df.empty:
            st.warning("No data after applying filters.")
        else:
            lane_factor = LANE_FACTORS_IRC.get(lane_config, 0.75)
            total_esal = df["ESAL"].sum()
            daily_esal = total_esal * lane_factor * PCI_CONFIG["DIRECTIONAL_FACTOR"]
            annual_msa = (daily_esal * 365) / 1_000_000

            timeline = []
            for year in range(0, design_life + 1):
                if growth_rate == 0:
                    cum_msa = annual_msa * year
                else:
                    cum_msa = annual_msa * (((1 + growth_rate) ** year - 1) / growth_rate)

                design_pci = calculate_pci_logistic(cum_msa, 0, "design")
                actual_pci = calculate_pci_logistic(
                    cum_msa, current_age + year, "actual"
                )
                rating = get_pci_rating(actual_pci)

                timeline.append(
                    {
                        "Year": year,
                        "Pavement Age": current_age + year,
                        "Cumulative MSA": round(cum_msa, 6),
                        "Design PCI": design_pci,
                        "Actual PCI": actual_pci,
                        "Condition": rating["rating"],
                        "Action": rating["action"],
                    }
                )

            pci_df = pd.DataFrame(timeline)
            st.session_state.pci_timeline = pci_df

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Annual MSA (Million)", f"{annual_msa:.6f}")
            with col2:
                st.metric("Total ESAL", f"{total_esal:.2f}")
            with col3:
                st.metric("Lane Factor", f"{lane_factor}")
            with col4:
                st.metric("Current Age (years)", f"{current_age}")

            st.dataframe(pci_df[pci_df["Year"] % 2 == 0], use_container_width=True)

            maint = detect_maintenance_period(
                pci_df,
                maintenance_threshold=maintenance_threshold,
                failure_threshold=failure_threshold,
            )
            if maint is None:
                st.markdown(
                    f"""
<div class="success-box">
<strong>✅ NO MAINTENANCE REQUIRED</strong><br>
PCI remains above {maintenance_threshold} for {design_life} years.
</div>
""",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
<div class="warning-box">
<strong>⚠️ MAINTENANCE PERIOD DETECTED</strong><br>
Year {maint['start_year']} - {maint['end_year']} ({maint['duration']} years)<br>
PCI Drop: {maint['start_pci']} → {maint['end_pci']}
</div>
""",
                    unsafe_allow_html=True,
                )

            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(pci_df["Year"], pci_df["Design PCI"], "-o", label="Design PCI")
            ax.plot(pci_df["Year"], pci_df["Actual PCI"], "-o", label="Actual PCI")
            ax.axhline(
                maintenance_threshold,
                color="green",
                linestyle="--",
                label=f"Maintenance ({maintenance_threshold})",
            )
            ax.axhline(
                failure_threshold,
                color="red",
                linestyle="--",
                label=f"Failure ({failure_threshold})",
            )
            ax.set_xlabel("Year")
            ax.set_ylabel("PCI")
            ax.set_title(f"PCI Deterioration - {project_name}")
            ax.grid(alpha=0.3)
            ax.legend()
            st.pyplot(fig)

# ============================================================================
# TAB: EXPORT
# ============================================================================

with tab_export:
    st.markdown(
        "<div class='section-header'>📥 EXPORT REPORT</div>",
        unsafe_allow_html=True,
    )

    if st.session_state.df_analyzed is None:
        st.warning("⚠️ Please upload and analyze data first")
    else:
        if st.button("Generate Excel Report"):
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                st.session_state.df_analyzed.to_excel(
                    writer, sheet_name="RAW_DATA", index=False
                )
                if st.session_state.vdf_table is not None:
                    st.session_state.vdf_table.to_excel(
                        writer, sheet_name="VDF_ANALYSIS", index=False
                    )
                if st.session_state.spectrum_tables is not None:
                    for name, df_spec in st.session_state.spectrum_tables.items():
                        df_spec.to_excel(
                            writer, sheet_name=f"{name.upper()}_SPECTRUM", index=False
                        )
                if st.session_state.pci_timeline is not None:
                    st.session_state.pci_timeline.to_excel(
                        writer, sheet_name="PCI_TIMELINE", index=False
                    )

            buffer.seek(0)
            st.download_button(
                label="📥 Download Excel",
                data=buffer,
                file_name=f"{project_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.markdown("### 📄 PDF Report")
        pdf_buf = build_pdf_report(project_name, project_location)
        if pdf_buf is None:
            st.info("Run VDF and PCI analysis first to enable PDF export.")
        else:
            st.download_button(
                label="📄 Download PDF Report",
                data=pdf_buf,
                file_name=f"{project_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
            )

