//////////////////////////////////////////////////////////////////
// common header-files and definitions 
// used by the FEOS library
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#ifndef LIB_DEFINITS_H
#define LIB_DEFINITS_H

//////////////////////////////////////////////////////////////////
// header-files:

#include "COMMON-00_DEFINITS.H"
#include "COMMON-01_UTILITIES.H"
#include "COMMON-02_READFILE.H"
#include "LIB-01_TF_SERVICES.H"
#include "LIB-02_TF_TABLE.H"
#include "LIB-04_IONMOD.H"

//////////////////////////////////////////////////////////////////
// definitions:

#define MATERIAL_DATABASE_PATH "./FEOS_Material-DB.dat"
#define TF_TABLE_PATH          "./FEOS_TF-Table_1197.dat"

//////////////////////////////////////////////////////////////////
// constants:

const double 
  PRECISION_TABLE = 1.0e-8,            // TABLEtools
  C1              = 0.143289792062,    // sqrt(2.0) / (Pi*Pi)    temperature treatment
  C1_CGS          = C1*2.34425256e40,  // C_1 in cgs units
  ZERO            = 1.0e-60,           // in order to cut off too big values from 1/x
  T_ZERO          = 1.0e-4,            // lower borders for density and temperature; take care for stability and constant ZERO!
  RHO_ZERO        = 1.0e-50;           // T in eV, RHO in g/ccm; important for low temperature Maxwell construction 
  
const int 
  WORDS_IN_TF_LINE = 6;                // No of words in line of TF-table 

// QIPscheme / Thomas-Fermi:
const double
  TSCALE      = 1.5e-24,               // for T-> oo Extrapolation  
  EPS_DPDR    = 0.001,
  Ho          = 1.48731045e13,         // *1.5 for u -> 0 Extrapolation
  QIPmult_rho = pow( 10.0, 0.1 ),
  QIPmult_T   = pow( 10.0, 0.2 ),
  Einfinity   = -2.003755854614347e+13, //  der Wert fuer Eoo(Thomas-Fermi)
  Emin        = -2.003769258311165e+13; // - 4e7 : dieser Wert sichert positive Energien
const int 
  P_OFFSET = 0;

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
// eof.