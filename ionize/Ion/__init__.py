import warnings
from math import copysign
import json
import numpy as np

from ..Aqueous import Aqueous
from ..BaseIon import BaseIon


from ..constants import faraday


class Ion(BaseIon):

    """Describe an ion dissolved in aqueous solution.

    Args:
        name (str): The chemical name of the ion.

        z (list): A list of valence states for the ion, as integers.

        pKa_ref (list): The pKa of each valence at the refernce temperature,\
        as floats.

        absolute_mobility_ref (list): The signed absolute mobility of each\
        valence at the reference temperature, as floats, in units\
        of m^2/V/s. Expect O(10^-8).

        dH (list): The enthalpy of dissociation of each valence, at the\
        reference temperature, as floats.

        dCp (list): The change in heat capacity of dissociation of each\
        valence, at the reference temperature, as floats.

        nightingale_data (function): A function describing absolute\
        mobility as a function of temperature, for special ions.

        T (float): The temperature to use to calculate the properties of the
        ions, in degrees C.

        T_ref (float): The reference temperature for the reference properties,
        in degrees C.

    Attributes:
        z (list): A list of valence states for the ion, as integers.

        pKa (list): The pKa of each valence at the refernce temperature,\
            as floats.

        absolute_mobility (list): The signed absolute mobility of each\
            valence at the reference temperature, as floats, in units\
            of m^2/V/s. Expect O(10^-8).

        T (float): The temperature to use to calculate the properties of the\
            ions, in degrees C.

    Raises:
        None

    Example:
        To to initialize an Ion, call as:

        >>> ionize.Ion('my_acid', [-1, -2], [1.2, 3.4], [-10e-8, -21e-8])
    """
    _solvent = Aqueous()

    # _aD is treated as a constant, though it does vary slightly with temp.
    _aD = 1.5             # L^3/2 mol^-1

    # The reference properties of the ion are stored and used to calculate
    # properties at the current temperature.
    _pKa_ref = []
    _absolute_mobility_ref = []  # m^2/V/s.
    _T_ref = 25

    # The properties of the ions are stored in public variables.
    # These are the properties at the current temperature, or are treated
    # as temperature independant.
    pKa = None
    absolute_mobility = None
    dH = None
    dCp = None
    z0 = None
    T = 25

    # If the Ion is in a solution object, copy the pH and I of the Solution
    # locally for reference, in a private variable. Also store the Onsager-
    # Fouss mobility in _actual_mobility.
    _pH = None
    _I = None
    _actual_mobility = None

    def __init__(self, name, z, pKa_ref, absolute_mobility_ref,
                 dH=None, dCp=None, nightingale_data=None,
                 T=25.0, T_ref=25.0):
        """Initialize an Ion object."""
        # Copy properties into the ion.

        self.name = name
        self.T = T
        self._T_ref = T_ref
        self.dH = dH
        self.dCp = dCp
        self.nightingale_data = nightingale_data
        if self.nightingale_data:
            self._nightingale_function = np.poly1d(self.nightingale_data['fit'])
        else:
            self._nightingale_function = None

        # Copy in the properties that should be lists, as long as they are
        # single values or iterables.
        try:
            self.z = [zp for zp in z]
        except:
            self.z = [z]

        try:
            self._pKa_ref = [p for p in pKa_ref]
        except:
            self._pKa_ref = [pKa_ref]

        try:
            self._absolute_mobility_ref = [m for m in absolute_mobility_ref]
        except:
            self._absolute_mobility_ref = [absolute_mobility_ref]

        self.temperature_adjust()

        # Force the sign of the fully ionized mobilities to match the sign of
        # the charge. This command provides a warning.
        if not all([copysign(z, m) == z for z, m in zip(self.z,
                    self.absolute_mobility)]):
            self.absolute_mobility = [copysign(m, z) for z, m in zip(self.z,
                                      self.absolute_mobility)]
            warnings.warn("Mobility signs and charge signs don't match.")

        # Check that z is a vector of integers
        assert all([isinstance(zp, int) for zp in self.z]), \
            "z contains non-integer"

        # Check that the pKa is a vector of numbers of the same length as z.
        assert len(self.pKa) == len(self.z), "pKa is not the same length as z"

        assert len(self.absolute_mobility) == len(self.z), '''absolute_mobility is not
                                                    the same length as z'''

    def temperature_adjust(self):
        """Temperature adjust the ion."""
        if self.T == self._T_ref:
            self.pKa = self._pKa_ref
            self.absolute_mobility = self._absolute_mobility_ref
        else:
            self.pKa = self._correct_pKa()
            if self._nightingale_function:
                self.absolute_mobility = \
                    [self._nightingale_function(self.T).tolist() *
                     10.35e-11 * z / self._solvent.viscosity(self.T)
                     for z in self.z]
                if (self.T > self.nightingale_data['max']) or \
                        (self.T < self.nightingale_data['min']):
                    warnings.warn('Temperature outside range'
                                  'for nightingale data.')
            else:
                self.absolute_mobility =\
                    [self._solvent.viscosity(self._T_ref) /
                     self._solvent.viscosity(self.T)*m
                     for m in self._absolute_mobility_ref]
        # After storing the ion properties, ensure that the properties are
        # sorted in order of charge. All other ion methods assume that the
        # states will be sorted by charge.
        self._z_sort()
        self._set_z0()

    def _z_sort(self):
        """Sort the charge states from lowest to highest."""
        # Zip the lists together and sort them by z.
        self.z, self.pKa, self.absolute_mobility =\
            zip(*sorted(zip(self.z, self.pKa, self.absolute_mobility)))
        self.z = list(self.z)
        self.pKa = list(self.pKa)
        self.absolute_mobility = list(self.absolute_mobility)

        full = set(range(min(self.z), max(self.z)+1, 1)) - set([0])
        assert set(self.z) ^ full == set(), "Charge states missing."

        return None

    def Ka(self):
        """Set the Kas based on the pKas.

        These values are not corrected for ionic strength.
        """
        return [10.**-p for p in self.pKa]

    def _set_z0(self):
        """Set the list of charge states with 0 inserted."""
        self.z0 = sorted([0]+self.z)
        return None

    def set_T(self, T):
        """Return a new ion at the specified temperature."""
        self.T = T
        self.temperature_adjust()
        return self

    def serialize(self, nested=False):
        serial = {'__ion__': True,
                  'name': self.name,
                  'z': self.z,
                  'pKa_ref': self._pKa_ref,
                  'absolute_mobility_ref': self._absolute_mobility_ref,
                  'dH': self.dH,
                  'dCp': self.dCp,
                  'nightingale_data': self.nightingale_data}

        if nested:
            return serial
        else:
            return json.dumps(serial)

    def save(self, filename):
        with open(filename, 'w') as file:
            json.dump(self.serialize(), file)

    from .ionization_fraction import ionization_fraction
    from .activity_coefficient import activity_coefficient
    from .effective_mobility import effective_mobility
    from .Ka_eff import Ka_eff
    from .L import L
    from .molar_conductivity import molar_conductivity
    from .robinson_stokes_mobility import robinson_stokes_mobility
    from .correct_pKa import _correct_pKa, _vant_hoff, _clark_glew
    from .diffusivity import diffusivity

if __name__ == '__main__':
    pass
