import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# Apheresis system parameters for lymphodepletion with hematocrit factors
LYMPHODEPLETION_SETTINGS = {
    'Spectra Optia': {
        'flow_range': (40, 60),
        'plasma_removal_range': (15, 30),
        'acd_ratio_range': (11, 14),
        'hct_impact': 0.3,  # 30% hematocrit sensitivity
        'rbc_base_contam': 3.0  # Base RBC contamination (×10⁹)
    },
    'Haemonetics': {
        'flow_range': (35, 55),
        'plasma_removal_range': (10, 25),
        'acd_ratio_range': (10, 13),
        'hct_impact': 0.7,  # 70% hematocrit sensitivity
        'rbc_base_contam': 6.0  # Higher base contamination for Haemonetics
    }
}

# UV bag parameters
BAG_TYPES = {
    'Spectra Optia (Polyethylene)': {'absorption': 0.9, 'scattering': 5.5, 'thickness': 0.20},
    'Haemonetics (PVC)': {'absorption': 1.3, 'scattering': 7.0, 'thickness': 0.25}
}

# HSC-sparing UV dose ranges
UV_DOSE_RANGES = {
    'UV-A': (1.0, 5.0),  # HSC-sparing range up to 5 J/cm²
    'UV-B': (0.005, 0.4)  # HSC-sparing range 0.005-0.4 J/cm²
}

def calculate_lymphodepletion(tlc, lymph_percent, hct, system, lamp_power, target_dose, 
                            use_hood, custom_distance, bag_type, flow_rate, 
                            plasma_removal, acd_ratio):
    """Enhanced lymphodepletion calculator with hematocrit adjustment"""
    
    params = LYMPHODEPLETION_SETTINGS[system]
    
    # 1. Hematocrit efficiency correction (normalized to 40% Hct)
    hct_efficiency = 1 - params['hct_impact'] * (hct - 40)/40
    
    # 2. Apheresis performance factors with Hct adjustment
    interface_factor = 1.25 * hct_efficiency  # Fixed optimal interface position
    flow_factor = flow_rate / params['flow_range'][1] * hct_efficiency
    depletion_factor = 1.2 * hct_efficiency  # Simplified depletion factor
    
    # 3. Product composition estimation with Hct-adjusted RBC contamination
    mnc_conc = (tlc * (lymph_percent/100) * 1.3 * 6 * flow_factor * interface_factor)
    rbc_contam = params['rbc_base_contam'] * (hct/40) * (1 - plasma_removal/25)
    
    # 4. UV delivery calculations
    transmission = np.exp(-np.sqrt(3 * BAG_TYPES[bag_type]['absorption'] * 
                          (BAG_TYPES[bag_type]['absorption'] + BAG_TYPES[bag_type]['scattering'])) * 
                         BAG_TYPES[bag_type]['thickness'])
    distance = custom_distance if not use_hood else 20  # Hood uses fixed 20cm
    intensity = (lamp_power * 1000 * 0.85 * transmission) / (4 * np.pi * distance**2)
    
    # 5. Dose adjustment with Hct-impacted shielding
    shielding = (0.015 * mnc_conc) + (0.03 * rbc_contam * (hct/40))
    effective_dose = target_dose * transmission * max(1 - shielding, 0.3) * depletion_factor
    exp_time = (effective_dose / (intensity / 1000)) / 60
    
    # Calculate predicted outcomes
    lymph_viability = 100*np.exp(-1.5*effective_dose)
    cd34_viability = 100*np.exp(-0.25*effective_dose)
    
    return {
        'mnc_conc': mnc_conc,
        'rbc_contam': rbc_contam,
        'depletion_factor': depletion_factor,
        'effective_dose': effective_dose,
        'exp_time': exp_time,
        'transmission': transmission,
        'intensity': intensity,
        'lymph_viability': lymph_viability,
        'cd34_viability': cd34_viability,
        'hct_efficiency': hct_efficiency,
        'params': params,
        'distance': distance
    }

def main():
    st.set_page_config(page_title="UV-based Sensitizer-free HSCs-Sparing Lymphodepletion Calculator", layout="wide")
    st.title("UV-based Sensitizer-free HSCs-Sparing Lymphodepletion Calculator")
    
    # Input parameters in sidebar
    with st.sidebar:
        st.header("Donor CBC Parameters")
        col1, col2 = st.columns(2)
        with col1:
            tlc = st.slider("TLC (×10³/µL)", 5.0, 50.0, 10.0, 0.5)
        with col2:
            lymph_percent = st.slider("Lymphocyte %", 10, 90, 40)
        
        hct = st.slider("Donor's Hematocrit (%)", 20.0, 60.0, 40.0, 0.1,
                       help="Critical for apheresis efficiency and RBC contamination")
        
        st.header("System Configuration")
        system = st.selectbox("Apheresis System", list(LYMPHODEPLETION_SETTINGS.keys()))
        bag_type = st.selectbox("UV Bag Type", list(BAG_TYPES.keys()))
        
        st.header("Treatment Parameters")
        uv_type = st.selectbox("UV Type", ["UV-A", "UV-B"], 
                             help="UV-C not applicable for HSC-sparing applications")
        
        # Set HSC-sparing dose ranges based on UV type
        dose_range = UV_DOSE_RANGES[uv_type]
        if uv_type == "UV-A":
            target_dose = st.slider("Target Dose (J/cm²)", 
                                   dose_range[0], dose_range[1], 3.0, 0.1,
                                   help="HSC-sparing range: 1-5 J/cm²")
        else:  # UV-B
            target_dose = st.slider("Target Dose (J/cm²)", 
                                   dose_range[0], dose_range[1], 0.2, 0.005,
                                   help="HSC-sparing range: 0.005-0.4 J/cm²")
        
        lamp_power = st.slider("UV Lamp Power (W)", 5, 50, 25)
        use_hood = st.checkbox("Use Laminar Hood (fixed 20cm distance)", value=True)
        
        if not use_hood:
            custom_distance = st.slider("Custom Distance (cm)", 10, 50, 15, 1,
                                       help="Distance between UV source and treatment bag")
        else:
            custom_distance = 20  # Default when hood is used
        
        st.header("Apheresis Settings")
        
        # Flow rate adjustment guidance
        flow_default = 45
        if hct > 45:
            flow_default = 40 if system == 'Haemonetics' else 50
        flow_rate = st.slider("Flow Rate (mL/min)", 
                            LYMPHODEPLETION_SETTINGS[system]['flow_range'][0], 
                            LYMPHODEPLETION_SETTINGS[system]['flow_range'][1], 
                            flow_default)
        
        plasma_removal = st.slider("Plasma Removal (%)", 
                                 LYMPHODEPLETION_SETTINGS[system]['plasma_removal_range'][0], 
                                 LYMPHODEPLETION_SETTINGS[system]['plasma_removal_range'][1], 20)
        
        # ACD ratio adjustment for high Hct
        acd_default = 12
        if hct > 45:
            acd_default = 11 if system == 'Haemonetics' else 13
        acd_ratio = st.slider("ACD Ratio (1:X)", 
                            LYMPHODEPLETION_SETTINGS[system]['acd_ratio_range'][0], 
                            LYMPHODEPLETION_SETTINGS[system]['acd_ratio_range'][1], 
                            acd_default)
    
    # Calculate results
    results = calculate_lymphodepletion(tlc, lymph_percent, hct, system, lamp_power, target_dose,
                                      use_hood, custom_distance, bag_type, flow_rate,
                                      plasma_removal, acd_ratio)
    
    # Display results
    st.subheader("HSC-Sparing Lymphodepletion Protocol")
    
    # System Efficiency Panel
    eff_color = "red" if results['hct_efficiency'] < 0.85 else "green"
    st.markdown(f"""
    <div style="background-color:#f0f2f6;padding:10px;border-radius:5px;margin-bottom:20px">
        <h4 style="color:{eff_color}">System Efficiency: {results['hct_efficiency']:.2f} (1.0 = ideal at 40% Hct)</h4>
        <p>Hematocrit impact: <b>{LYMPHODEPLETION_SETTINGS[system]['hct_impact']*100:.0f}%</b> sensitivity | 
        RBC contamination base: <b>{LYMPHODEPLETION_SETTINGS[system]['rbc_base_contam']} ×10⁹</b></p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("MNC Concentration", f"{results['mnc_conc']:.1f} ×10⁶/mL")
        st.metric("RBC Contamination", f"{results['rbc_contam']:.1f} ×10⁹", 
                delta=f"{(results['rbc_contam']-LYMPHODEPLETION_SETTINGS[system]['rbc_base_contam']):.1f} vs baseline",
                delta_color="inverse")
    with col2:
        st.metric(f"Effective {uv_type} Dose", f"{results['effective_dose']:.2f} J/cm²")
        st.metric("Treatment Time", f"{results['exp_time']:.1f} minutes")
    with col3:
        st.metric("Lymphocyte Viability", f"{results['lymph_viability']:.1f}%")
        st.metric("CD34+ Viability", f"{results['cd34_viability']:.1f}%")
        st.metric("Distance", f"{results['distance']} cm")
    
    # Create plots
    st.subheader("HSC-Sparing Response Analysis")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    # Dose-response plot
    doses = np.linspace(0, UV_DOSE_RANGES[uv_type][1]*1.2, 100)
    ax1.plot(doses, 100*np.exp(-1.5*doses*results['transmission']*results['depletion_factor']), 'r-', label='Lymphocytes')
    ax1.plot(doses, 100*np.exp(-0.25*doses*results['transmission']), 'b-', label='CD34+')
    ax1.axvline(results['effective_dose'], color='k', linestyle='--', label='Selected Dose')
    ax1.set_title(f'{uv_type} Dose-Response (HSC-Sparing)')
    ax1.set_xlabel(f'{uv_type} Dose (J/cm²)')
    ax1.set_ylabel('Viability (%)')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Time-response plot
    times = np.linspace(0, max(results['exp_time']*2, 90), 100)
    time_doses = (results['intensity']/1000) * (times * 60)
    ax2.plot(times, 100*np.exp(-1.5*time_doses*results['depletion_factor']), 'r-', label='Lymphocytes')
    ax2.plot(times, 100*np.exp(-0.25*time_doses), 'b-', label='CD34+')
    ax2.axvline(results['exp_time'], color='k', linestyle='--', label='Estimated Time')
    ax2.set_title(f'{uv_type} Time-Response (HSC-Sparing)')
    ax2.set_xlabel('Time (minutes)')
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    st.pyplot(fig)
    
    # Clinical guidance with HCT considerations
    st.subheader("UV-based Sensitizer-free Advanced Lymphodepletion Calculator")
    st.markdown(f"""
    ### {system} HSC-Sparing Lymphodepletion Hct-adjusted Protocol {hct}%
    
    **UV Parameters ({uv_type}):**
    - Target Dose: {target_dose:.3f} J/cm² (HSC-sparing range: {UV_DOSE_RANGES[uv_type][0]}-{UV_DOSE_RANGES[uv_type][1]} J/cm²)
    - Effective Dose: {results['effective_dose']:.3f} J/cm²
    - Treatment Time: {results['exp_time']:.1f} minutes
    - Source Distance: {results['distance']} cm
    
    **Apheresis Settings:**
    - Flow Rate: {flow_rate} mL/min
    - Plasma Removal: {plasma_removal}%
    - ACD Ratio: 1:{acd_ratio}
    
    **Expected Outcomes:**
    - Lymphocyte viability: {results['lymph_viability']:.1f}%
    - CD34+ viability: {results['cd34_viability']:.1f}%
    
    **Clinical Notes:**
    - UV-A (5 J/cm² max) preserves HSC function while depleting lymphocytes
    - UV-B (0.4 J/cm² max) preserves 25% CAFC while abolishing PHA responses
    - For high Hct (>45%): reduce flow rate by 10-20% and increase plasma removal
    """)

if __name__ == "__main__":
    main()
