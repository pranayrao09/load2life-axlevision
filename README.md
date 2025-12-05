# 🛣️ Load2Life-AxleVision

**IRC 37:2018 Compliant Pavement Management & Traffic Analysis System**

An advanced web-based tool developed by **L&T EDRC CHENNAI** - Transportation Infrastructure Division for comprehensive pavement asset management, traffic data analysis, and maintenance scheduling.

---

## 📊 Features

### 1. **VDF Analysis** (Vehicle Damage Factor)
- Quantify relative damage contribution of each vehicle type
- ESAL calculation per IRC 37:2018 Fourth Power Law
- Visual pie charts and bar graphs
- Overload detection and reporting

### 2. **Axle Load Spectrum Analysis**
- Distribution profiles for Single, Tandem, and Tridem axles
- 3 histogram visualizations side-by-side
- IRC limit overlays (80 kN, 148 kN, 224 kN)
- Frequency and percentage breakdowns

### 3. **PCI Deterioration Modeling**
- 20-30 year pavement condition prediction
- Logistic S-curve model (design vs actual)
- Maintenance window detection
- Cost projections per maintenance action
- PCI rating scale (Excellent to Worst)

### 4. **Professional Reporting**
- One-click Excel export
- All charts and data included
- Multi-sheet workbooks
- Ready for stakeholder presentations

---

## 🔐 Standards Compliance

✅ **IRC 37:2018** - Flexible Pavement Design Life & ESAL Calculation  
✅ **IRC-82:2023** - Pavement Condition Index Rating  
✅ **ASTM D6433-20** - PCI Calculation Methodology  
✅ **AASHTO Guide** - Pavement Design & Analysis  
✅ **MoRTH Specifications** - Indian Highway Standards  

---

## 🚀 Quick Start

### Local Installation

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/load2life-axlevision.git
cd load2life-axlevision

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run application
streamlit run app.py
```

**App opens at:** http://localhost:8501

### Cloud Deployment (Streamlit Cloud)

1. Push repository to GitHub
2. Go to https://streamlit.io/cloud
3. Click "New app"
4. Select this repository
5. Deploy! ✅

**Live URL:** https://YOUR_USERNAME-load2life-axlevision.streamlit.app

---

## 📋 Data Input Format

### Required Columns:
- `Location Detail` - Road location/segment
- `Direction` - Traffic direction (NB/SB/EB/WB)
- `VehicleType` - Vehicle category (HCV, MCV, LCV, etc.)
- `AxleConfig` - Axle configuration (1.1, 1.2, 1.22, 1.222)
- `Front1` - Front axle load (kg)
- `Rear1` - First rear axle load (kg)
- `Rear2` - Second rear axle load (kg)
- `Rear3` - Third rear axle load (kg)
- `TotalWeightKg` - Total vehicle weight (kg)

### Supported Formats:
- Excel (.xlsx, .xls)
- CSV (.csv)

### Sample Data Structure:
```
Location Detail | Direction | VehicleType | AxleConfig | Front1 | Rear1 | Rear2 | TotalWeightKg
NH-44 Km-10     | NB        | HCV         | 1.22       | 5000   | 5500  | 5500  | 16000
NH-44 Km-10     | SB        | MCV         | 1.2        | 3000   | 3500  | 0     | 6500
```

---

## 🎯 Usage Workflow

1. **Upload Data** → Select Excel/CSV file with traffic survey data
2. **Filter** → Choose location and direction (optional)
3. **Analyze** → Select analysis type:
   - VDF (Vehicle Damage Factor)
   - Spectrum (Axle Load Distribution)
   - PCI (Pavement Condition Index)
4. **Visualize** → Interactive charts with hover, zoom, pan
5. **Export** → One-click Excel report generation

---

## 💼 Business Applications

### Asset Lifecycle Management
- Predict pavement life with actual traffic data
- Schedule maintenance during optimal windows
- Budget 20-30 year capital plans
- Avoid emergency repairs (cost: 5x preventive)

### Toll Collection & Enforcement
- Identify overly-damaging vehicle categories
- Implement weight-based toll structures
- Track enforcement effectiveness
- Quantify "damage paid for" ratios

### Structural Design Justification
- Pavement thickness based on actual traffic
- Design layer moduli using IRC-37 & AASHTO
- Faster approvals with data-backed designs
- Avoid over/under-design

### Maintenance Prioritization
- Rank roads by maintenance urgency
- Allocate budget to highest-impact projects
- Minimize traffic disruption
- Data-driven policy for MoRTH/PWD

---

## 🛠️ Technical Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit (Web UI) |
| Backend | Python 3.9+ |
| Data Processing | Pandas, NumPy |
| Visualization | Plotly, Matplotlib |
| Data Export | Openpyxl |
| Hosting | Streamlit Cloud (AWS) |

---

## 📊 Calculations & Methodology

### ESAL Calculation (IRC 37:2018)

```
ESAL = (Load/Standard Load)⁴

Standards:
- Single Axle (65 kN): ESAL = (Load/65)⁴
- Single Axle (80 kN): ESAL = (Load/80)⁴
- Tandem Axle (148 kN): ESAL = (Load/148)⁴
- Tridem Axle (224 kN): ESAL = (Load/224)⁴
```

### PCI Deterioration Model

```
Logistic S-Curve: PCI = 100 / [1 + exp(a + b×MSA)]

Design Curve (a=-5.0, b=1.8): Ideal conditions
Actual Curve (a=-5.0, b=2.5): Real deterioration
Age Factor: 0.08 multiplier/year (accelerates decay)
```

### MSA Calculation

```
Annual MSA = (Daily ESAL × Lane Factor × Direction Factor × 365) / 1,000,000

Lane Factors (IRC Table 3):
- 2-lane: 0.50
- 4-lane: 0.75
- 6-lane: 0.60
- 8-lane: 0.45
```

---

## 📈 Output Formats

### Interactive Dashboards
- VDF pie chart (ESAL distribution)
- VDF bar chart (individual VDF values)
- Spectrum histograms (3 types: single, tandem, tridem)
- PCI deterioration curve (design vs actual)
- Maintenance window highlighting

### Excel Reports
- RAW_DATA sheet (all processed records)
- VDF_ANALYSIS sheet (vehicle type statistics)
- PCI_TIMELINE sheet (year-by-year projection)
- KEY_METRICS sheet (executive summary)

---

## 🔒 Data Privacy & Security

- ✅ No data stored on cloud servers
- ✅ Local processing in browser
- ✅ HTTPS encryption in transit
- ✅ No third-party data sharing
- ✅ Compliant with data protection regulations

---

## 📞 Support & Contact

**Developed by:** L&T EDRC CHENNAI - Transportation Infrastructure Division

**Email:** support@lnt-edrc.com

**Documentation:** See in-app "Guide" tab for detailed help

**Version:** 1.0 (December 2025)

**Status:** Industrial Grade | Production Ready

---

## 🤝 Contributing

Contributions, bug reports, and feature requests welcome!

---

## 📄 License

Proprietary - L&T EDRC CHENNAI

---

## 🙏 Acknowledgments

- IRC 37:2018 (Indian Roads Congress)
- ASTM D6433-20 Standard
- AASHTO Pavement Design Guide
- MoRTH Specifications

---

## 🎯 Future Roadmap

- [ ] Multi-lane traffic simulation
- [ ] Climate impact modeling
- [ ] AI-based anomaly detection
- [ ] Real-time sensor integration
- [ ] Mobile app (iOS/Android)
- [ ] API for third-party integration
- [ ] Advanced reporting (PDF/PPT)
- [ ] Multi-language support

---

**Last Updated:** December 2025

**🛣️ Build Better Roads with Data-Driven Insights**
