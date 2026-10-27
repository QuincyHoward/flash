//////////////////////////////////////////////////////////////////
// service routines for isotherms, isochores, hugoniots, etc. 
// used by the SHOWEOS table visualization tool
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#ifndef SE_SERVICES_H 
#define SE_SERVICES_H

//////////////////////////////////////////////////////////////////
// header-files:
 
#include "SE-00_DEFINITS.H"

//////////////////////////////////////////////////////////////////
// constants:

const double HUG_FACTOR = 0.1;    // for rootfinder in Rankine-Hugoniot
const double T_MULT_HUG = 1.005;  // stepsize for next Hugoniot point 
const double R_MULT_HUG = 1.005;  // stepsize for next Hugoniot point
const double P_MULT_HUG = 1.1;    // stepsize for data storage

//////////////////////////////////////////////////////////////////
// rountines in SE-03_SERVICES.C:

int    Check_Density( Qtable*, double, double );
int    Check_Temperature( Qtable*, double, double );
int    Check_Quantity( Qtable*, int, int, int );
void   GetPointArray( double*, int, double*, int*, int, int, int, double, double );
void   GetQuantityName ( char*, int, int, int );
double GetQuantity( int, Qtable*, double, double, int, int, Units* );
void   GetUnitsName( char*, int, int, Units* );
double GetUnits( int, Units* );
void   GetMeshParameters( Qtable*, char*, Units*, int, int*, int*, int*, int*,
                          int*, int*, int*, double*, double*, 
                          int*, int*, int*, double*, double* );
void   GetOutputQuantity( Qtable*, char*, Units*, int, int, char*, char*, 
                          char*, int*, double*, int*, char*, char* );
void   Isotherms( Qtable* , char*, Units*, int, int );
void   Isochores( Qtable* , char*, Units*, int, int );
void   Isentropes( Qtable* , char*, Units*, int, int );
void   Mountain( Qtable* , char*, Units*, int, int );
void   Hugoniot( Qtable* , char*, Units*, int, int );
void   SinglePoint( Qtable* , char* , char*, Units*, int, int ); 

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
// eof.