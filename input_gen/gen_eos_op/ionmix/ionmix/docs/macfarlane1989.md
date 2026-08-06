# IONMIX — A Code for Computing the Equation of State and Radiative Properties of LTE and Non-LTE Plasmas

> **Authors**: J.J. MacFarlane
>
> **Affiliation**: Fusion Technology Institute, University of Wisconsin–Madison
>
> **Published**: *Computer Physics Communications* 56 (1989) 259–278
>
> **CPC Program Library Catalogue Number**: ABJT

---

## Abstract

A detailed description of a code developed to compute the energetics and radiative properties of high temperature, low-to-moderate density plasmas is presented. Steady-state ionization and excitation populations are determined by detailed balancing arguments and rate coefficients based on the hydrogenic ion approximation. We consider contributions from bound–bound, bound–free, free–free and electron scattering processes in evaluating extinction and emission coefficients at several hundred well-placed photon energies, which are then used to compute multi-group Planck and Rosseland mean opacities.

---

## Program Summary

| Item | Description |
|------|-------------|
| **Title** | IONMIX |
| **Catalogue number** | ABJT |
| **Computer** | VAX 8600 (Madison Academic Computing Center, UW-Madison) |
| **Operating system** | VAX/VMS |
| **Programming language** | FORTRAN 77 |
| **High speed storage** | 156 kwords (32-bit words) |
| **Peripherals** | line printer, ten disk files |
| **Lines of code** | 5027 |

**Keywords**: LTE and non-LTE plasma physics, equations of state, opacities, semi-classical atomic physics

---

## 1. Introduction

The equation of state and radiative properties of plasmas are often required to study the physical properties of laboratory and astrophysical plasmas [1,2]. Quite often the conditions in a problem are such that the plasma can be considered to be at either of two extremes:

1. **Local thermodynamic equilibrium (LTE)**: 3-body collisions dominate all atomic processes.
2. **Non-LTE, "coronal" equilibrium**: the gas density is sufficiently low that 2-body radiative effects are the dominant mechanism of recombination and deexcitation.

However, a number of problems exist in which the plasma can migrate between these two extremes, thus requiring a solution in which both 2-body and 3-body atomic processes are fully considered. Examples include stellar atmospheres, and inertial confinement fusion (ICF) target chambers, where gas densities can vary from $10^{14}$–$10^{19}$ ions/cm$^3$ and temperatures from $10^4$–$10^7$ K.

The IONMIX code computes the steady-state ionization and excitation populations for a mixture of up to 10 different atomic species. The radiative absorption, emission, and scattering coefficients are calculated at a large number (~several hundred) of photon energies, and integrated over selected energy intervals to determine the multigroup Planck and Rosseland mean opacities. The code also calculates thermodynamic properties such as specific energy, average charge state, pressure, and heat capacity.

---

## 2. Atomic Processes

### 2.1. Ionization Populations

The ionization populations for IONMIX are computed for steady-state conditions using detailed balance arguments. The atomic processes considered are:

- **Collisional ionization**: $X^m + e^- \rightarrow X^{m+1} + e^- + e^-$
- **Radiative recombination**: $X^{m+1} + e^- \rightarrow X^m + h\nu$
- **Dielectronic recombination**: $X^{m+1} + e^- \rightarrow (X^m)^{**} \rightarrow X^m + h\nu$
- **Collisional (three-body) recombination**: $X^{m+1} + e^- + e^- \rightarrow X^m + e^-$

Throughout this paper, the subscripts $j$ and $k$ refer to the ionization state and gas species, respectively.

**Units**:

| Quantity | Unit |
|----------|------|
| Energy | eV |
| Temperature | eV |
| Time | s |
| Charge | esu |
| Length | cm |
| Electron/ion density | cm$^{-3}$ |
| Mass density | g/cm$^3$ |
| Specific energy | J/g |
| Heat capacity | (J/g)/eV |

Under steady-state conditions, the number of ions in the $j$th ionization state is:

$$f_{jk} = \frac{N_k}{Z_k} \frac{ \prod_{m=0}^{j-1} R_{m,m+1} }{ 1 + \sum_{m=0}^{j-1} \prod_{i=0}^{m} R_{i,i+1} } \tag{2.1}$$

where $N_k = \sum_{j=0}^{Z_k} P_{jk}$ is the total number of species $k$ nuclei and $Z_k$ is the atomic number of species $k$. $R_{m,m+1}$ is the ratio of the collisional ionization rate to the sum of the recombination rates:

$$R_{m,m+1} = \frac{C_{\text{coll}}^m}{\alpha_{rr}^{m+1} + \alpha_{dr}^{m+1} + \alpha_{\text{coll}}^{m+1}} \tag{2.2}$$

where $\alpha_{rr}$, $\alpha_{dr}$, and $\alpha_{\text{coll}}$ are the radiative, dielectronic, and collisional recombination rates, respectively.

**Collisional ionization** involves the reaction $X^j + e^- \rightarrow X^{j+1} + e^- + e^-$. The rate is [3]:

$$C_{\text{coll}} = \left(1.09 \times 10^{-6} \frac{\text{cm}^3}{\text{s}}\right) \frac{n_e n_j \xi \bar{g} e^{-x}}{T^{3/2} \phi^{1/2} x} \tag{2.3}$$

where $n_e$ and $n_j$ are the densities of electrons and ions in the $j$th ionization state, $T$ is the electron temperature in eV, $\phi$ is the ionization potential in eV, $x = \phi/T$, $\xi$ is the number of electrons in the outer shell, and $\bar{g}$ is the Gaunt factor (empirical formula from ref. [3]).

IONMIX uses the calculated ionization potentials of Carlson et al. [4] as default values for: H, He, Li, Be, B, C, N, O, F, Ne, Na, Mg, Si, S, Ar, Kr, Xe. The ionization potentials for other elements must be supplied by the user.

**Collisional recombination** rate (the reverse process of collisional ionization):

$$\alpha_{\text{coll}} = C_{\text{coll}} \frac{n_e L_{j+1}}{L_j} \left( \frac{h^2}{2\pi m_e k_B T} \right)^{3/2} e^{\phi/T} \tag{2.4}$$

where $L_j$ and $L_{j+1}$ are the electronic partition functions for the $j$th and $(j+1)$th ionization stages.

**Radiative recombination rate** (Seaton [6]):

$$\alpha_{rr} = \left(5.20 \times 10^{-14} \frac{\text{cm}^3}{\text{s}}\right) \frac{n_e n_{j+1} \sqrt{\phi/T}}{3(j+1)} \left[ \frac{x}{x+\phi/T} \right] E_1(x) \tag{2.5}$$

where $E_1(x)$ is the first exponential integral, evaluated using polynomial fits [7].

**Dielectronic recombination rate** (Burgess [8], modified by Post et al. [3]):

$$\alpha_{dr} = \left(2.40 \times 10^{-9} \frac{\text{cm}^3}{\text{s}}\right) n_e n_{j+1} T^{-3/2} B(j+1) \sum_i A(y) e^{-E_\infty(i)/T} \tag{2.6}$$

where:
- $B(z) = z^{1/2} (z+1)^{5/2} (z^2 + 13.4)^{-1/2}$
- $E_\infty(i) = 13.6 \text{ eV} (j+2)$
- $a = 1 + 0.015 (j+1)^3 / (j+2)^2$
- $v_1$, $v_n$ are effective principal quantum numbers

For $A(y)$ and $D(j+1)$:

$$A(y) = \begin{cases}
y^{1/2} / (1 + 0.105y + 0.015y^2), & \Delta n = 0 \\
y / [2 + 0.420y + 0.060y^2], & \Delta n \neq 0
\end{cases}$$

$$D(j+1) = \begin{cases}
[0.5 / (qN_\infty)], & \Delta n = 0 \\
(qN_\infty)^2 / [(qN_\infty)^2 + 667], & \Delta n \neq 0
\end{cases}$$

where $q = j+2$ and $N_\infty \approx 1.51 \times 10^{17} (j+1)^6 T^{1/2} / n_e^{1/7}$.

The ionization populations are found by solving Eq. (2.1) iteratively because the electron density is not known in advance.

**Fig. 1** shows the computed ionization fractions for a low density carbon plasma as a function of the electron temperature (dashed curves = odd states C$^{1+}$, C$^{3+}$, C$^{5+}$; solid curves = even states C$^{0+}$, C$^{2+}$, C$^{4+}$, C$^{6+}$). At temperatures above ~200 eV, essentially all of the carbon becomes fully ionized.

### 2.2. Excitation Populations

After the ionization populations are determined, IONMIX computes the excitation populations for each ion. The populations of each excited state are calculated by balancing:

- **Collisional excitation** (rate $C_{\text{exc}}^{m \to n}$)
- **Collisional deexcitation** (rate $C_{\text{deexc}}^{n \to m}$)
- **Radiative decay** (Einstein spontaneous emission coefficient $A_{nm}$)

In the high density limit, collisional processes dominate and populations follow Boltzmann statistics. In the low density limit, radiative decay dominates.

For the excitation energies, a Bohr-like model is used:

$$E_n = -\Phi_j \left( \frac{n_0}{n} \right)^2 \quad (n \geq n_0) \tag{2.8}$$

where $n_0$ is the principal quantum number of the outermost electron in its ground state, and $\Phi_j$ is the ionization potential.

The transition energy for excitation from $n$ to $m$ ($m > n$):

$$\Delta E_{nm} = \Phi_j n_0^2 \left( \frac{1}{n^2} - \frac{1}{m^2} \right) \tag{2.9}$$

**Collisional excitation rate** [10]:

$$C_{\text{exc}} = \left(1.58 \times 10^{-7} \frac{\text{cm}^3}{\text{s}}\right) \frac{n_e n_n g_m f_{nm} \bar{g}_{nm}}{T^{1/2} \Delta E_{nm}} e^{-\Delta E_{nm}/T} \tag{2.7}$$

where $f_{nm}$ is the oscillator strength, $\bar{g}_{nm}$ is the Gaunt factor (Van Regemorter [10] for $\Delta n \neq 0$, tables from ref. [3] for $\Delta n = 0$).

**Collisional deexcitation rate** (from detailed balance):

$$C_{\text{deexc}}^{n \to m} = C_{\text{exc}}^{m \to n} \frac{g_n}{g_m} e^{\Delta E_{nm}/T} \tag{2.10}$$

**Radiative decay rate** (Einstein $A$ coefficient):

$$A_{nm} = \left(4.32 \times 10^7 \frac{\text{cm}^3}{\text{s}}\right) \frac{g_m}{g_n} (\Delta E_{nm})^2 f_{nm} \tag{2.11}$$

**Relative excitation populations**:

$$\frac{n_n}{n_m} = \frac{(g_n/g_m) e^{-\Delta E_{nm}/T}}{1 + \dfrac{2.74 \times 10^7 f_{nm} (\Delta E_{nm})^2}{n_e \bar{g}_{nm} T^{1/2}}} \tag{2.12}$$

The radiative decay term (denominator second term) becomes less important as the electron density increases. Actual populations are obtained by normalizing the relative fractions to the total number of ions in each ionization state.

---

## 3. Equations of State

After the ionization and excitation populations are determined, calculation of the equation of state properties is straightforward.

**Specific energy** (relative to the ground state energy of the neutral atom):

$$E = \frac{n_{\text{tot}}}{\rho} \Bigg[ \frac{3}{2} (1 + \langle Z \rangle) T + \sum_k f_k \sum_{j=1}^{Z_k} f_{jk} \left( \sum_{i=0}^{j-1} \Phi_{i,k} + \sum_{\text{exc}} \epsilon_{i,k} \right) \Bigg] \tag{3.1}$$

where:
- $\rho$ = mass density
- $n_{\text{tot}}$ = total number density of nuclei
- $f_k = n_k/n_{\text{tot}}$ = relative species fraction
- $f_{jk} = n_{jk}/n_k$ = ionization fraction
- $f_{ijk} = n_{ijk}/n_{jk}$ = excitation fraction
- The last two terms represent energy stored in ionization and excitation

**Average charge state**:

$$\langle Z \rangle = \sum_k f_k \sum_{j=1}^{Z_k} j \cdot f_{jk} \tag{3.2}$$

**Pressure** (ideal gas, assuming negligible interparticle potentials):

$$P = (1 + \langle Z \rangle) n_{\text{tot}} k_B T \tag{3.3}$$

where $T$ represents the temperature of both the electrons and ions (assumed to be in equilibrium).

**Fig. 2** shows the average charge state for Ne as a function of ion density at 3 different temperatures (3, 30, and 300 eV), comparing full IONMIX results with only 2-body (coronal) and only 3-body (Saha) recombination models.

In addition, IONMIX also calculates the specific heat, $(\partial E / \partial T)_V$, and the temperature derivative of the average charge state, $(\partial \langle Z \rangle / \partial T)_V$, by numerical differentiation.

---

## 4. Radiative Properties

### 4.1. Absorption, Emission, and Scattering Coefficients

The radiative properties are calculated using a hydrogenic ion model. The absorption coefficient and emissivity include contributions from free–free (bremsstrahlung), bound–free (photoionization), and bound–bound (photoexcitation) transitions.

**Absorption coefficient**:

$$\begin{aligned}
\kappa_\nu = &\sum_k \sum_j \sum_n \sum_{m>n} \left[ n_{njk} - \frac{g_n}{g_m} n_{mjk} \right] \sigma_{nm}^{bb}(\nu) \\
&+ \sum_k \sum_j \sum_n \left[ n_{njk} - n_{njk}^* e^{-h\nu/k_B T} \right] \sigma_{njk}^{bf}(\nu) \\
&+ n_e \sum_k \sum_j n_{jk} \left[ 1 - e^{-h\nu/k_B T} \right] \sigma_{jk}^{ff}(\nu) + s_\nu \tag{4.1}
\end{aligned}$$

**Emissivity**:

$$\begin{aligned}
\eta_\nu = \frac{2h\nu^3}{c^2} \Bigg[ &\sum_k \sum_j \sum_n \sum_{m>n} \frac{g_n}{g_m} n_{mjk} \sigma_{nm}^{bb}(\nu) \\
&+ \sum_k \sum_j \sum_n n_{njk}^* e^{-h\nu/k_B T} \sigma_{njk}^{bf}(\nu) \\
&+ n_e \sum_k \sum_j n_{jk} e^{-h\nu/k_B T} \sigma_{jk}^{ff}(\nu) \Bigg] \tag{4.2}
\end{aligned}$$

where $n_{njk}^*$ is the LTE population of state $n_{njk}$ using the computed ion density of the post-ionization ground state, and $\sigma$ are the cross sections.

In the high density (LTE) limit, $n_{mjk} = n_{njk} (g_m/g_n) e^{-\Delta E/T}$ and $n_{njk}^* = n_{njk}$. Thus, stimulated emission reduces to $(1 - e^{-h\nu/k_B T})$, and the Kirchhoff–Planck relation $\eta_\nu = \kappa_\nu B_\nu$ holds. Because this relation is not true in general, IONMIX tabulates absorption and emission opacities separately.

**Free–free cross section** (hydrogenic approximation) [11]:

$$\sigma^{ff}(\nu) = \left(2.40 \times 10^{-37} \frac{\text{cm}^5}{\text{eV}^{1/2}}\right) \frac{\langle Z^2 \rangle \bar{g}_{ff}}{(h\nu) T^{1/2}} \tag{4.3}$$

where the free–free Gaunt factor uses a fit from Karzas and Latter [12]:

$$\bar{g}_{ff} = 1 + 0.44 \exp\left[ -\frac{1}{4}(y^2 + \eta^2) \right]$$

with:
- $y = \log_{10}(13.6 Z_{\text{eff}}^2 / T)$
- $\eta = \langle Z^2 \rangle / \langle Z \rangle$
- $\langle Z^2 \rangle = \sum_{j=1}^{Z_k} f_{jk} j^2$

**Bound–free cross section** [5]:

$$\sigma^{bf}(\nu) = \left(1.99 \times 10^{-14} \frac{\text{cm}^2}{\text{eV}^{1.5}}\right) \frac{(j+1)^4 F_n}{n (h\nu)^3} \tag{4.4}$$

where $F_n$ is the unoccupied fraction of the shell with principal quantum number $n$.

**Bound–bound cross section**:

$$\sigma^{bb}(\nu) = \left(2.65 \times 10^{-6} \frac{\text{cm}^2}{\text{eV}}\right) f_{nm} L(\Gamma, \nu) \tag{4.5}$$

where $f_{nm}$ is the oscillator strength and $L(\Gamma, \nu)$ is the line shape function.

**Lorentzian line profile**:

$$L^L(\Gamma, \Delta\nu) = \frac{\Gamma / (4\pi)}{(\Delta\nu)^2 + (\Gamma/4\pi)^2}$$

**Voigt line profile** (default):

$$L^V(\Gamma, \Delta\nu) = \frac{H(a_{\text{voigt}}, \Delta\nu/\nu_D)}{\sqrt{\pi} \nu_D}$$

where $H$ is the Voigt function.

**Damping factor** $\Gamma$:

$$\begin{aligned}
\Gamma &= \Gamma_{\text{nat}} + \Gamma_{\text{Dop}} + \Gamma_{\text{coll}} \\
      &= 2.29 \times 10^{-6} (\Delta E_{nm})^2 \\
      &\quad + 1.41 \times 10^{-11} \Delta E_{nm} \sqrt{T/A} \\
      &\quad + 4.58 \times 10^{-6} \sqrt{T/A} n_e \tag{4.6}
\end{aligned}$$

where $A$ is the atomic weight in amu, $\bar{v} = \sqrt{T/A}$, and $\Delta E_{nm}$ is the transition energy.

**Thomson scattering coefficient**:

$$s_T = (6.66 \times 10^{-25}~\text{cm}^2) n_e^{\text{eff}} \tag{4.6}$$

where $n_e^{\text{eff}}$ includes contributions from bound electrons with binding energy less than the photon energy.

**Plasma wave scattering coefficient** [13]:

$$s_{pw} = \begin{cases}
(\omega_p / \omega)^2 s_T, & h\nu < h\nu_{pw} \\
0, & h\nu \geq h\nu_{pw}
\end{cases} \tag{4.7}$$

where $\omega_p = \sqrt{4\pi e^2 n_e / m_e}$ is the plasma frequency.

**Figs. 3 and 4** show the absorption and emission coefficients for a 90% Ar + 10% Li plasma at $T = 5$ eV and $n = 3 \times 10^{17}$ cm$^{-3}$, where bound–bound transitions and photoionization edges are clearly visible.

### 4.2. Opacity Calculations

The Rosseland and Planck mean opacities are obtained by integrating the absorption, emission, and scattering coefficients over the photon energy. IONMIX computes Planck and Rosseland mean group opacities for up to 50 photon energy bins.

**Planck mean group opacity for absorption** (photon energy range $x_g = h\nu_g/k_B T_R$ to $x_{g+1} = h\nu_{g+1}/k_B T_R$) [5]:

$$\sigma_{P,g}^A = \frac{1}{\rho} \frac{\displaystyle \int_{x_g}^{x_{g+1}} B_\nu(T_R) \kappa_\nu \, dx}{\displaystyle \int_{x_g}^{x_{g+1}} B_\nu(T_R) \, dx} \tag{4.8}$$

**Planck mean group opacity for emission**:

$$\sigma_{P,g}^E = \frac{1}{\rho} \frac{\displaystyle \int_{x_g}^{x_{g+1}} \eta_\nu \, dx}{\displaystyle \int_{x_g}^{x_{g+1}} B_\nu(T_R) \, dx} \tag{4.9}$$

**Rosseland mean group opacity**:

$$\frac{1}{\sigma_{R,g}} = \frac{1}{\rho} \frac{\displaystyle \int_{x_g}^{x_{g+1}} \frac{1}{\kappa_\nu + s_\nu} \frac{\partial B_\nu}{\partial T_R} \, dx}{\displaystyle \int_{x_g}^{x_{g+1}} \frac{\partial B_\nu}{\partial T_R} \, dx} \tag{4.10}$$

The integration uses a trapezoidal method with logarithmic interpolation between adjacent points. By placing ~5–10 mesh points near each line transition energy and ~2 near each photoionization edge, the numerical accuracy is approximately a few percent.

**Mean opacities integrated over all photon energies**:

$$\sigma_{P,\text{tot}} = \frac{\displaystyle \sum_g \sigma_{P,g} \int_{x_g}^{x_{g+1}} B_\nu(T_R) \, dx}{\displaystyle \int_0^\infty B_\nu(T_R) \, dx} \tag{4.11}$$

$$\sigma_{R,\text{tot}} = \frac{\displaystyle \int_0^\infty \frac{\partial B_\nu}{\partial T_R} \, dx}{\displaystyle \sum_g \frac{1}{\sigma_{R,g}} \int_{x_g}^{x_{g+1}} \frac{\partial B_\nu}{\partial T_R} \, dx} \tag{4.12}$$

**Plasma cooling rate** (per ion per free electron):

$$\Lambda(T) = \frac{4 \sigma_{SB} \rho T^4}{n_e n_{\text{tot}}} \sigma_P^E \tag{4.13}$$

where $\sigma_{SB}$ is the Stefan–Boltzmann constant.

---

## 5. File Descriptions

### Table 1: Input/Output Files

| Name | Type | Unit | Description |
|------|------|:----:|-------------|
| **IONMXINP** | input | 5 | NAMELIST input file |
| **IONMXOUT** | output | 6 | Text output file |
| **ATOMnn** | input | 7 | File containing ionization potentials for atomic number $n$ |
| **CNRDEOS** | output | 11 | EOS and opacity data in CONRAD format |
| **IMPLOT01** | output | 12 | Absorption coefficient vs. photon energy |
| **IMPLOT02** | output | 13 | Opacities vs. temperature |
| **IMPLOT03** | output | 14 | Emission coefficient vs. photon energy |
| **IMPLOT04** | output | 15 | Opacities vs. density |
| **IMPLOT05** | output | 16 | Charge states and cooling rates vs. temperature |
| **IMPLOT09** | output | 19 | Fractional ionization populations vs. temperature |

All file names have the usual ".DAT" VAX extension.

**ATOMnn.DAT** files: one floating point number per record. The first record contains data for the neutral atom, the second for the singly ionized particle, etc. Free format is used. Example for oxygen (ATOM08.DAT):

```
 16.4
 82.8
122.0
146.0
699.0
836.0
```

Default ionization potentials are supplied for: H, He, Li, Be, B, C, N, O, F, Ne, Na, Mg, Al, Si, P, S, Cl, Ar, K, Ca, Sc, Ti, V, Cr, Mn, Fe, Ni, Cu, Kr, Xe.

---

## 6. Subroutines and Their Functions

A flow diagram of the IONMIX subroutines is shown in Fig. 5.

```
                   IONMIX FLOW DIAGRAM

    INPUT ── IDATE ── TIME
       │
    ENERGY ── SAHA / CORONA
       │
    EOS
       │
    MESHHV
       │
    ABSCON ── LINES ── ABSLIN
       │
    OPACYS ── OPACGP ── OPACBB
       │
    OWT1 ── OWTF
```

| Subroutine | Purpose |
|------------|---------|
| **IONMIX** | Main program; drives computation by looping over (T, n) points |
| **INPUT** | Reads namelist input; initializes temperature/density grids and files |
| **IDATE** | VAX system subroutine; returns date |
| **TIME** | VAX system subroutine; returns time |
| **ENERGY** | Finds ionization and excitation populations; computes specific energy |
| **SAHA** | Computes Saha ionization equilibrium (LTE) |
| **CORONA** | Computes coronal ionization equilibrium (non-LTE) |
| **ATMLV** | Computes excitation level populations for each ion |
| **EOS** | Computes specific energy, heat capacity, and derivatives |
| **MESHHV** | Generates photon energy mesh including points near line centers and photoionization edges |
| **ABSCON** | Calculates absorption, emission, and scattering coefficients |
| **LINES** | Handles bound–bound transitions using detailed line-by-line calculation |
| **ABSLIN** | Computes contribution from a single bound–bound transition |
| **OPACYS** | Computes multigroup Planck and Rosseland mean opacities |
| **OPACGP** | Integrates over a single energy group |
| **OPACBB** | Computes line contributions analytically for rapid calculation of group opacities |
| **OWT1** | Writes results for each (T, n) point to IONMXOUT |
| **OWTF** | Writes EOS/opacity tables in CONRAD format |

The code is written in FORTRAN 77 with the sole exception being the NAMELIST read in subroutine INPUT. Two VAX system subroutines are called (IDATE and TIME). Otherwise, the program is transportable to other mainframe computers.

---

## 7. Test Run

The test run input is a low-density nitrogen plasma with the following parameters:

- One gas: N ($Z=7$), $A=14.007$
- 20 temperature points, $\log_{10}$ spacing $\Delta \log T = 0.2$, starting at $T=1$ eV
- 1 density point: $n = 10^{14}$ cm$^{-3}$
- 50 mesh points per opacity group, 5 points near each bound–bound transition
- ISW controls: coronal model with 3-body recombination (ISW(6)=3), Voigt line profiles (ISW(14)=0), default group boundaries

The test run output (Tab. 3) shows results at each (T, n) point: temperature, electron density, average charge state, specific energy, pressure, Planck and Rosseland mean opacities, and group opacities.

---

## 8. ISW Control Switches (Table 5)

| Index | Default | Description |
|:-----:|:-------:|-------------|
| 1 | 0 | User supplies ionization potentials (0=no, 1=yes) |
| 2 | 0 | Compute opacities (0=yes, 1=no) |
| 3 | 0 | Request debug output (# = # of subroutines) |
| 4 | 0 | Compute heat capacity and dZ/dT (0=yes, 1=no) |
| 5 | 0 | Copy input to output (0=yes, 1=no) |
| 6 | 3 | Ionization model: 0=interpolated, 1=Saha, 2=coronal, 3=coronal with 3-body |
| 7 | 0 | Not used |
| 8 | 0 | File format for CONRAD: 0=no, 1/12=CONRAD, 2/12=SESAME |
| 9 | 0 | Maximum principal quantum number in populations (0=code picks) |
| 10 | 0 | Not used |
| 11 | 0 | Include $\Delta n=0$ transitions (0=yes, 1=no) |
| 12 | 0 | Restrict ions to ground state (0=no, 1=yes) |
| 13 | 0 | Specify group boundaries: 0=default, 1=user specifies, 2=default T-dependent |
| 14 | 0 | Line profile: 0=Voigt, 1=Lorentzian |
| 15 | 2 | Max principal quantum # in opacity: if<0, npqmax=-ISW15; if>0, npqmax=ISW15+ground state # |
| 16 | 0 | Include dielectronic recombination (0=yes, 1=no) |
| 17 | 0 | Include bremsstrahlung (0=yes, 1=no) |
| 18 | 0 | Include photoionization (0=yes, 1=no) |
| 19 | 0 | Include line contributions: 0=yes, 1=no, 2=core/wings computed separately |
| 20 | 0 | Include scattering contributions (0=yes, 1=no) |

---

## 9. Constants Array CON (Table 6)

| Index | Default | Description |
|:-----:|:-------:|-------------|
| 1 | 0.0 | Reserved |
| 2 | 1.0E-10 | Minimum species concentration to compute bb and bf transitions |
| 3 | 1.0E-10 | Minimum ionization concentration |
| 4 | 1.0E-10 | Minimum atomic state concentration |
| 5 | 1.0E+10 | Range (in FWHM line widths) to compute bb contribution |
| 6 | 1.0E+01 | Width (in FWHM line widths) of line core |
| 7 | 1.0E+01 | Absorption coefficients weighted by Planck function when $1/\text{con}7 < h\nu/kT < \text{con}7$ |
| 8 | 0.0 | Reserved |
| 9 | 1.0 | Multiplier for mesh point spacing around lines |
| 10 | 0.0 | Reserved |

---

## 10. Sample Results

### Table 3: Test Run Output (excerpt)

Ionization potentials for N ($Z=7$):

| State | Potential (eV) |
|:-----:|:--------------:|
| 0 | 13.4 |
| 1 | 32.0 |
| 2 | 51.6 |
| 3 | 82.6 |
| 4 | 103.1 |
| 5 | 524.0 |
| 6 | 643.3 |

Sample results at $T=1.0$ eV, $n=10^{14}$ cm$^{-3}$:
- Electron density: $2.81 \times 10^4$ cm$^{-3}$
- Average charge state: $2.81 \times 10^{-10}$
- Specific energy: $2.80 \times 10^{-9}$ J/g
- Pressure: $1.38 \times 10^{-10}$ dyne/cm$^2$

**Figs. 6–8** show the specific energy, average charge state, and cooling rate for a low-density nitrogen plasma as a function of temperature, calculated using the full IONMIX model.

**Figs. 9–10** show the Rosseland and Planck group opacities for a high-density SiO$_2$ plasma at $T=500$ eV, $n=8.43\times10^{21}$ cm$^{-3}$.

---

## References

[1] M. Uesaka, R.R. Peterson and G.A. Moses, *Nucl. Fusion* 24 (1984) 1137.
[2] R.V. Jensen, D.E. Post, W.H. Grasberger, C.B. Tarter, and W.A. Lokke, *Nucl. Fusion* 17 (1977) 1187.
[3] D. Mihalas, *Stellar Atmospheres* (Freeman, San Francisco, 1978).
[4] T.A. Carlson, C.W. Nestor Jr., N. Wasserman and J.D. McDowell, *At. Data Nucl. Data Tables* 2 (1970) 63.
[5] See, e.g.: *Radiation Hydrodynamics in Stars and Compact Objects*, eds. D. Mihalas and K.-H.A. Winkler (Springer, New York, 1986).
[6] M.J. Seaton, *Mon. Not. R. Astron. Soc.* 119 (1959) 81.
[7] W.J. Karzas and R. Latter, *Astrophys. J. Suppl.* 6 (1961) 167.
[8] A. Burgess, *Astrophys. J.* 141 (1965) 1588.
[9] H. Van Regemorter, *Astrophys. J.* 136 (1962) 906.
[10] W. Lotz, *Z. Phys.* 216 (1968) 241.
[11] H.A. Bethe and E.E. Salpeter, *Quantum Mechanics of One- and Two-Electron Atoms* (Springer, Berlin, 1957).
[12] W.J. Karzas and R. Latter, *Astrophys. J. Suppl.* 6 (1961) 167.
[13] J. Dawson and C. Oberman, *Phys. Fluids* 5 (1962) 517.
[14] R.R. Peterson et al., *University of Wisconsin Fusion Technology Institute Report* UWFDM-670 (1985).

---

> **Document version**: 1.0
>
> **Conversion date**: 2026-07-02
>
> **Original PDF**: `macfarlane1989.pdf` — Computer Physics Communications 56 (1989) 259–278
>
> **Note**: All equations have been re-typeset in LaTeX format based on the original paper. Figures are not reproduced here; refer to the original publication for graphical content.
