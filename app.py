import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# Apheresis system parameters for lymphodepletion
LYMPHODEPLETION_SETTINGS = {
    'Spectra Optia': {
        'interface_range': (0.3, 1.5),  # Lower interface for aggressive depletion
        'flow_range': (40, 60),         # Reduced flow for better separation
        'plasma_removal_range': (15, 30), # Higher plasma removal
        'acd_ratio_range': (11, 14)     # More anticoagulant for long runs
    },
    'Haemonetics': {
        'interface_range': (0.3, 1.5),
        'flow_range': (35, 55),
        'plasma_removal_range': (10, 25),
        'acd_ratio_range': (10, 13)
    }
}

# UV-C bag parameters (254nm)
BAG_TYPES = {
    'Spectra Optia (Polyethylene)': {'absorption': 0.9, 'scattering': 5.5, 'thickness': 0.20},
    'Haemonetics (PVC)': {'absorption': 1.3, 'scattering': 7.0, 'thickness': 0.25}
}

def calculate_lymphodepletion(tlc, lymph_percent, system, lamp_power, target_dose, 
                            use_hood, bag_type, interface_pos, flow_rate, 
                            plasma_removal, acd_ratio):
    """Enhanced lymphodepletion calculator with apheresis integration"""
    
    params = LYMPHODEPLETION_SETTINGS[system]
    
    # 1. Apheresis performance factors
    interface_factor = 1.5 - (interface_pos / params['interface_range'][1])
    flow_factor = flow_rate / params['flow_range'][1]
    depletion_factor = 1.8 - (interface_pos * 0.5)
    
    # 2. Product composition estimation
    mnc_conc = (tlc * (lymph_percent/100) * 1.3 * 6 * flow_factor * interface_factor)
    rbc_contam = np.mean([3.0, 6.0]) * (1 - plasma_removal/25)
    
    # 3. UV-C delivery calculations
    transmission = np.exp(-np.sqrt(3 * BAG_TYPES[bag_type]['absorption'] * 
                          (BAG_TYPES[bag_type]['absorption'] + BAG_TYPES[bag_type]['scattering'])) * 
                         BAG_TYPES[bag_type]['thickness'])
    distance = 20 if use_hood else 15
    effective_intensity = (lamp_power * 1000 * 0.85 * transmission) / (4 * np.pi * distance**2)
    
    # 4. Dose adjustment
    shielding = (0.015 * mnc_conc) + (0.03 * rbc_contam)
    effective_dose = target_dose * transmission * max(1 - shielding, 0.3) * depletion_factor
    exp_time = (effective_dose / (effective_intensity / 1000)) / 60
    
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
        'lymph_viability': lymph_viability,
        'cd34_viability': cd34_viability,
        'params': params
    }

def main():
    st.set_page_config(page_title="Lymphodepletion Calculator", layout="wide")
    st.title("Advanced Lymphodepletion Calculator")
    
    # Input parameters in sidebar
    with st.sidebar:
        st.header("Patient Parameters")
        tlc = st.slider("TLC (×10³/µL)", 5.0, 50.0, 10.0, 0.5)
        lymph_percent = st.slider("Lymphocyte %", 10, 90, 40)
        
        st.header("System Configuration")
        system = st.selectbox("Apheresis System", list(LYMPHODEPLETION_SETTINGS.keys()))
        bag_type = st.selectbox("UV-C Bag Type", list(BAG_TYPES.keys()))
        
        st.header("Treatment Parameters")
        lamp_power = st.slider("UV-C Lamp Power (W)", 5, 50, 25)
        target_dose = st.slider("Target Dose (J/cm²)", 0.0, 6.0, 2.5, 0.1)
        use_hood = st.checkbox("Use Laminar Hood", value=True)
        
        st.header("Apheresis Settings")
        interface_pos = st.slider("Interface Position", 
                                LYMPHODEPLETION_SETTINGS[system]['interface_range'][0], 
                                LYMPHODEPLETION_SETTINGS[system]['interface_range'][1], 
                                0.8, 0.1)
        flow_rate = st.slider("Flow Rate (mL/min)", 
                            LYMPHODEPLETION_SETTINGS[system]['flow_range'][0], 
                            LYMPHODEPLETION_SETTINGS[system]['flow_range'][1], 45)
        plasma_removal = st.slider("Plasma Removal (%)", 
                                 LYMPHODEPLETION_SETTINGS[system]['plasma_removal_range'][0], 
                                 LYMPHODEPLETION_SETTINGS[system]['plasma_removal_range'][1], 20)
        acd_ratio = st.slider("ACD Ratio (1:X)", 
                            LYMPHODEPLETION_SETTINGS[system]['acd_ratio_range'][0], 
                            LYMPHODEPLETION_SETTINGS[system]['acd_ratio_range'][1], 12)
    
    # Calculate results
    results = calculate_lymphodepletion(tlc, lymph_percent, system, lamp_power, target_dose,
                                      use_hood, bag_type, interface_pos, flow_rate,
                                      plasma_removal, acd_ratio)
    
    # Display results
    st.subheader("Treatment Summary")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("MNC Concentration", f"{results['mnc_conc']:.1f} ×10⁶/mL")
        st.metric("RBC Contamination", f"{results['rbc_contam']:.1f} ×10⁹")
    with col2:
        st.metric("Effective UV-C Dose", f"{results['effective_dose']:.2f} J/cm²")
        st.metric("Treatment Time", f"{results['exp_time']:.1f} minutes")
    with col3:
        st.metric("Lymphocyte Viability", f"{results['lymph_viability']:.1f}%")
        st.metric("CD34+ Viability", f"{results['cd34_viability']:.1f}%")
    
    # Create plots
    st.subheader("Response Analysis")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    # Dose-response plot
    doses = np.linspace(0, 5, 100)
    ax1.plot(doses, 100*np.exp(-1.5*doses*results['transmission']*results['depletion_factor']), 'r-', label='Lymphocytes')
    ax1.plot(doses, 100*np.exp(-0.25*doses*results['transmission']), 'b-', label='CD34+')
    ax1.axvline(results['effective_dose'], color='k', linestyle='--', label='Selected Dose')
    ax1.set_title('Dose-Response Curve')
    ax1.set_xlabel('UV-C Dose (J/cm²)')
    ax1.set_ylabel('Viability (%)')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Time-response plot
    times = np.linspace(0, max(results['exp_time']*2, 90), 100)
    time_doses = (results['effective_intensity']/1000) * (times * 60)
    ax2.plot(times, 100*np.exp(-1.5*time_doses*results['depletion_factor']), 'r-', label='Lymphocytes')
    ax2.plot(times, 100*np.exp(-0.25*time_doses), 'b-', label='CD34+')
    ax2.axvline(results['exp_time'], color='k', linestyle='--', label='Estimated Time')
    ax2.set_title('Time-Response Curve')
    ax2.set_xlabel('Time (minutes)')
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    st.pyplot(fig)
    
    # Clinical guidance
    st.subheader("Clinical Protocol")
    st.markdown(f"""
    ### {system} Lymphodepletion Protocol
    **Apheresis Settings:**
    - Interface Position: {interface_pos} (Range: {results['params']['interface_range'][0]}-{results['params']['interface_range'][1]})
    - Flow Rate: {flow_rate} mL/min (Range: {results['params']['flow_range'][0]}-{results['params']['flow_range'][1]})
    - Plasma Removal: {plasma_removal}% (Range: {results['params']['plasma_removal_range'][0]}-{results['params']['plasma_removal_range'][1]})
    - ACD Ratio: 1:{acd_ratio} (Range: 1:{results['params']['acd_ratio_range'][0]}-1:{results['params']['acd_ratio_range'][1]})
    
    **Optimization Guidance:**
    - For **aggressive depletion**: Lower interface position (<0.8)
    - For **CD34+ preservation**: Maintain interface >1.0
    - For **RBC reduction**: Increase plasma removal (>20%)
    - For **stable product**: Use flow rate 40-50 mL/min
    """)

if __name__ == "__main__":
    main()
