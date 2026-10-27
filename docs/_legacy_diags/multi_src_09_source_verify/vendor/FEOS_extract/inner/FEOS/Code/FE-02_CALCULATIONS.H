//////////////////////////////////////////////////////////////////
// user-defined calculations using the FEOS library 
// used by the FEOS table generation tool
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#ifndef FE_CALCULATIONS_H
#define FE_CALCULATIONS_H

//////////////////////////////////////////////////////////////////
// header-files:

#include "FE-00_DEFINITS.H"   

//////////////////////////////////////////////////////////////////
// constants:

const double epsDT    = 0.001;		// precision of derivative for thermal expansion coefficient and heat capacity
const double eps_getR = 1.0e-8;	  // precision of bisection function for getting R(P)

//////////////////////////////////////////////////////////////////
// variables:

struct IsobaricExpansionTable {
  double *Tiso, *Rho0, *P, *alpha, *H, *Cp;
  int    Niso, NT;
  double MinT, MaxT;
};

//////////////////////////////////////////////////////////////////
// routines in FE-02_CALCULATIONS.C:

void   UserCalculations( int, char*, Qtable*, CriticalDataTable* );
double Get_Rho_by_TP( int, Qtable*, int, int, double, double, double, double );
void   IsobaricExpansion( int, IsobaricExpansionTable*, Qtable*, CriticalDataTable* );
void   write_isobaricdata( char*, IsobaricExpansionTable* );

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
// eof.