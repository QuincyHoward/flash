//////////////////////////////////////////////////////////////////
// service routines for (1) reading the TF-table file and
// (2) fast computation of the Fermi-Dirac function 
//     (F 1/2 and F 3/2) and its inverse function F^-1
// used by the FEOS library
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#ifndef LIB_TF_SERVICES_H
#define LIB_TF_SERVICES_H

//////////////////////////////////////////////////////////////////
// header-files:

#include "LIB-00_DEFINITS.H"

//////////////////////////////////////////////////////////////////
// variables:

struct TFtable {
  int    NR, NT;
  double *Te, *rho,   
         **Pe, **Ee, **Fe, **Se, **Q,
         **dPdT, **Virial, **Nernst;
};

//////////////////////////////////////////////////////////////////
// routines in LIB-01_TF_SERVICES.C:

void   get_memory( TFtable*, int , int, int );
void   write_TF_TABLE( char* , TFtable*, int );
void   clear_TF_TABLE( TFtable* );
void   read_TF_TABLE( char* , TFtable*, int );
double quickfermi_oh( double );
double quickfermi_th( double );
double fermi_1( int, double );

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
// eof.