"""Constants for use in the Emigrate solver."""

# Physical Constants
lpm3 = 1000.
faraday = 96485.34            # Faraday's const.[C/mol]
boltzmann = 1.38e-23          # Boltzmann's constant, [J/K]
gas_constant = 8.31           # Universal gas const. [J/mol*K]
permittivity = 8.85e-12       # Permativity of free space. [F/m]
avagadro = 6.02e23            # Avagadro's number, 1/mol
elementary_charge = 1.602e-19   # Charge of a proton, [C]

# Temperature Information
reference_temperature = 25.
kelvin_conversion = 273.15
# h_mobility = 362E-9/faraday   # Mobility of Hydroxide   # [m^2/s*V]/F
# oh_mobility = 205E-9/faraday  # Mobility of Hydronium   % [m^2/s*V]/F
# h_diffusivity = h_mobility / 1 * boltzmann * (temperature_K)
# oh_diffusivity = oh_mobility / -1 * boltzmann * (temperature_K)
