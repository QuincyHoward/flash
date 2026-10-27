//////////////////////////////////////////////////////////////////
// service routines for handling tables 
// used by the FEOS table generation tool
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#ifndef FE_TABTOOLS_H
#define FE_TABTOOLS_H

//////////////////////////////////////////////////////////////////
// header-files:

#include "FE-00_DEFINITS.H"

//////////////////////////////////////////////////////////////////
// constants:

const int MAXRATIO              = 6;   // EOS table from 10^-MAXRATIO..10^MAXRATIO 
const int MAX_INTERVAL_RT_TABLE = 20;  // max. No of INTERVALS in point grid (currently 13 = 6 + 6 + 1)

//////////////////////////////////////////////////////////////////
// routines in FE-01_TABTOOLS.C:

void getPointDensity( readfile*, int*, int*, char* );
void makeRTPointArray( int*, double*, double, double );
void write_criticaldata( char*, CriticalDataTable*, int, double, double );
void write_FEOS_format( char*, Qtable* );
void write_mexport_format( char*, Qtable* );
void write_301_format( char*, Qtable* );
void write_304_format( char*, Qtable* );
void write_305_format( char*, Qtable* );
void write_txt_format( char*, Qtable* );
void write_Rostock_format( char*, Qtable* );

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
// eof.