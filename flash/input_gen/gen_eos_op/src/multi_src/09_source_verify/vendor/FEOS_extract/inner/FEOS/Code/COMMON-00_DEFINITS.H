//////////////////////////////////////////////////////////////////
// common libraries and definitions 
// used by the FEOS library, the FEOS table generation tool, and by SHOWEOS
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#ifndef COMMON_DEFINITS_H
#define COMMON_DEFINITS_H

//////////////////////////////////////////////////////////////////
// libraries:

#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <iostream>
#include <fstream>

//////////////////////////////////////////////////////////////////
// definitions:

#define N_END          1
#define FREE_ARG       char*
#define ROSTOCK_SUFFIX "cst"
#define SES_301_SUFFIX "301"
#define SES_304_SUFFIX "304"
#define SES_305_SUFFIX "305"
#define PARFILE_SUFFIX "par"

//////////////////////////////////////////////////////////////////
// namespace:

using namespace std;

//////////////////////////////////////////////////////////////////
// constants:

const int 
  STRSIZE = 70;                        // max length of any string

// physical constants:
const double
  GAS_CONSTANT = 9.5856892e11;         // gas constant in erg / (eV mol)

// conversion factors:
const double 
  p_cgs     = 2.9454081590e14,         // dyne/cm2
  p_Mbar    = p_cgs / 1.0e12,          // [Megabars]
  t_cgs     = 27.21139625,             // eV  ( = e^2 / a0 )
  e_cgs     = 4.359748219e-11,         // [ergs]
  cgs2Joule = 1.0e-7,
  v_cgs     = 1.480184743e-25,         // [ccm]  = A_bohr^3
  eV2cgs    = 1.60217733e-12,          // eV --> cgs units 
  t_kelvin  = 8.617383848e-5,          // energy assoc with 1K
  M_proton  = 1.6726231e-24,           // [g]
  eV2Kelvin = 1.0/t_kelvin,
  cgs2Bar   = 1.0e-6,
  cgs2MBar  = 1.0e-12;

// SESAME:
const double
  cgs2ses_t   = 1.0/t_kelvin,
  cgs2ses_rho = 1.0,
  cgs2ses_p   = 1.0e-10,               // cgs units used in QEOS --- > SESAME units
  cgs2ses_e   = 1.0e-10;                   

// mathematical constants:
const double 
  Pi             = 3.14159265358979,
  Euler          = exp(1.0),
  wzwanzig       = pow( 10.0, 0.05 ),
  wzehn          = pow( 10.0, 0.10 ),
  wfuenf         = pow( 10.0, 0.2 ),
  pi4            = pow( Pi, 4.0),
  EIN_DRITTEL    = 1.0 / 3.0,
  ZWEI_DRITTEL   = 2.0 / 3.0,
  VIER_DRITTEL   = 4.0 / 3.0,
  FUENF_DRITTEL  = 5.0 / 3.0,
  ZWEI_FUENFTEL  = 2.0 / 5.0,
  DREI_FUENFTEL  = 3.0 / 5.0,
  WURZEL_ZWEI    = sqrt( 2.0 ),
  ACHT_DRITTEL   = 8.0 / 3.0,
  NEUN_ACHTEL    = 9.0 / 8.0,
  ZEHN_DRITTEL   = 10.0 / 3.0,
  ACHT_PI        = 8.0 * Pi,
  VIER_PI        = 4.0 * Pi,
  EIN_NEUNTEL    = 1.0 / 9.0,
  SIEBEN_DRITTEL = 7.0 / 3.0;

//////////////////////////////////////////////////////////////////
// variables:

// Qtable-structure - storage of all EOS data:
struct Qtable {    
  int      NRho, NT, Nelements;                     
  int      SESAMEnumber;
  double   RhoRef, TRef, BulkModulusRef;
  double   Atot, Ztot, Xtot;
  double   Ecoh, softsphere_n, softsphere_m, softsphere_A, softsphere_B;
  double   ElectronOffset, IonOffset;
  double   Tcalclimit, Rhocalclimit;
  double*  A;                       // indices cover 0..Nelements-1
  double*  Z;
  double*  X;    
  double*  T;                       // indices cover 0..NT-1
  double*  Rho;                     // indices cover 0..NRho-1
  double** P;                       // indices cover 0..NRho-1, 0..NT-1
  double** E;
  double** S;
  double** F;
  double** Pe;
  double** Ee;
  double** Se;
  double** Fe;
  double** Pi;
  double** Ei;
  double** Si;
  double** Fi;
  double** PTF;
  double** ETF;
  double** STF;
  double** FTF;
  double** Qtot; 
  double*** Q;                      // indices cover 0..NRho-1, 0..NT-1, 0..Nelements-1   
};

// storage of all critical data:
struct CriticalDataTable {
  int    Niso;
  double Trel, Tb;
  double Rhoc, Pc, Tc, Hc, Zc, Sc;
  double *Tiso, *Peq;               // indices cover 0..Niso-1
  double *Rhomax, *Rhomin;
  double *Pmax, *Pmin;   
  double *Rhol, *Rhov;
  double *Pl, *Pv;  
  double *Gl, *Gv;
  double *Hl, *Hv;
  double *Zl, *Zv;
};

// storage of units:
struct Units {
  double R, T, P, E, U, S, F, V, Q;
};

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
// eof.