import numpy as np
import matplotlib.pyplot as plt
from ipywidgets import interact, FloatSlider, Dropdown, IntSlider

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

def calculate_lymphodepletion(tlc=10.0, lymph_percent=40, system='Spectra Optia',
                            lamp_power=25, target_dose=3.0, use_hood=True,
                            bag_type='Spectra Optia (Polyethylene)',
                            interface_pos=0.8, flow_rate=45, plasma_removal=20, acd_ratio=12):
    """Enhanced lymphodepletion calculator with apheresis integration"""
    
    # 1. Apheresis performance factors
    params = LYMPHODEPLETION_SETTINGS[system]
    interface_factor = 1.5 - (interface_pos / params['interface_range'][1])  # Lower interface → more depletion
    flow_factor = flow_rate / params['flow_range'][1]
    depletion_factor = 1.8 - (interface_pos * 0.5)  # Aggressive depletion adjustment
    
    # 2. Product composition estimation
    mnc_conc = (tlc * (lymph_percent/100) * 1.3 * 6 * flow_factor * interface_factor)
    rbc_contam = np.mean([3.0, 6.0]) * (1 - plasma_removal/25)  # Higher removal → less RBC
    
    # 3. UV-C delivery calculations
    transmission = np.exp(-np.sqrt(3 * BAG_TYPES[bag_type]['absorption'] * 
                                  (BAG_TYPES[bag_type]['absorption'] + BAG_TYPES[bag_type]['scattering'])) * 
                         BAG_TYPES[bag_type]['thickness'])
    distance = 20 if use_hood else 15
    effective_intensity = (lamp_power * 1000 * 0.85 * transmission) / (4 * np.pi * distance**2)
    
    # 4. Dose adjustment with apheresis factors
    shielding = (0.015 * mnc_conc) + (0.03 * rbc_contam)
    effective_dose = target_dose * transmission * max(1 - shielding, 0.3) * depletion_factor
    exp_time = (effective_dose / (effective_intensity / 1000)) / 60
    
    # Generate plots
    plt.figure(figsize=(20, 7))
    
    # Plot 1: Dose-response with apheresis-adjusted depletion
    plt.subplot(1, 3, 1)
    doses = np.linspace(0, 5, 100)
    plt.plot(doses, 100*np.exp(-1.5*doses*transmission*depletion_factor), 'r-', label='Lymphocytes')
    plt.plot(doses, 100*np.exp(-0.25*doses*transmission), 'b-', label='CD34+')
    plt.axvline(effective_dose, color='k', linestyle='--')
    plt.title(f'Lymphodepletion Response\nInterface={interface_pos}, Flow={flow_rate}mL/min')
    plt.xlabel('UV-C Dose (J/cm²)')
    plt.ylabel('Viability (%)')
    plt.legend()
    plt.grid(alpha=0.3)
    
    # Plot 2: Time-response
    plt.subplot(1, 3, 2)
    times = np.linspace(0, max(exp_time*2, 90), 100)
    time_doses = (effective_intensity/1000) * (times * 60)
    plt.plot(times, 100*np.exp(-1.5*time_doses*depletion_factor), 'r-')
    plt.plot(times, 100*np.exp(-0.25*time_doses), 'b-')
    plt.axvline(exp_time, color='k', linestyle='--')
    plt.title('Treatment Time Course')
    plt.xlabel('Time (minutes)')
    plt.grid(alpha=0.3)
    
    # Apheresis parameters panel
    plt.subplot(1, 3, 3)
    plt.axis('off')
    text = f"""
    LYMPHODEPLETION PROTOCOL ({system})
    --------------------------------
    Apheresis Settings:
    - Interface Position: {interface_pos} (Range: {params['interface_range'][0]}-{params['interface_range'][1]})
    - Flow Rate: {flow_rate} mL/min (Range: {params['flow_range'][0]}-{params['flow_range'][1]})
    - Plasma Removal: {plasma_removal}% (Range: {params['plasma_removal_range'][0]}-{params['plasma_removal_range'][1]})
    - ACD Ratio: 1:{acd_ratio} (Range: 1:{params['acd_ratio_range'][0]}-1:{params['acd_ratio_range'][1]})
    
    Product Characteristics:
    - MNC Concentration: {mnc_conc:.1f} ×10⁶/mL
    - RBC Contamination: {rbc_contam:.1f} ×10⁹
    - Depletion Factor: {depletion_factor:.2f}
    
    UV-C Treatment:
    - Effective Dose: {effective_dose:.2f} J/cm²
    - Treatment Time: {exp_time:.1f} min
    
    Predicted Outcomes:
    - Lymphocyte Viability: {100*np.exp(-1.5*effective_dose):.1f}%
    - CD34+ Viability: {100*np.exp(-0.25*effective_dose):.1f}%
    
    Clinical Guidance:
    ► Lower interface (<1.0) → More aggressive depletion
    ► Moderate flow (40-50mL/min) → Balance speed/purity
    ► Higher plasma removal → Reduce RBC contamination
    ► Use 1:12 ACD ratio for optimal viability
    """
    plt.text(0.1, 0.1, text, fontsize=10, family='monospace',
            bbox={'facecolor': 'lightgray', 'alpha': 0.3})

    plt.tight_layout()
    plt.show()

# Interactive interface
interact(calculate_lymphodepletion,
         tlc=FloatSlider(value=10, min=5, max=50, step=0.5, description='TLC (×10³/µL):'),
         lymph_percent=FloatSlider(value=40, min=10, max=90, step=1, description='Lymph %:'),
         system=Dropdown(options=list(LYMPHODEPLETION_SETTINGS.keys()), description='System:'),
         lamp_power=FloatSlider(value=25, min=5, max=50, step=1, description='UV-C Lamp (W):'),
         target_dose=FloatSlider(value=2.5, min=0.0, max=6.0, step=0.1, description='Target Dose (J/cm²):'),
         use_hood=Dropdown(options=[True, False], description='Laminar Hood?'),
         bag_type=Dropdown(options=list(BAG_TYPES.keys()), description='Bag Type:'),
         interface_pos=FloatSlider(value=0.8, min=0.3, max=1.5, step=0.1, description='Interface Position:'),
         flow_rate=IntSlider(value=45, min=35, max=60, description='Flow Rate (mL/min):'),
         plasma_removal=IntSlider(value=20, min=10, max=30, description='Plasma Removal (%):'),
         acd_ratio=IntSlider(value=12, min=1, max=14, description='ACD Ratio (1:X):'))
