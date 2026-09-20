//////////////////////////////////////////////////////////////////
// routines for calculation of the Thomas-Fermi EOS of a mixture 
// used by the FEOS library
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#ifndef LIB_TF_MIXTURE_H
#define LIB_TF_MIXTURE_H 

//////////////////////////////////////////////////////////////////
// header-files:

#include "LIB-00_DEFINITS.H"
#include "LIB-05_EOS_SERVICES.H" 

//////////////////////////////////////////////////////////////////
// definitions:

#define SIGN(a,b) ((b) >= 0.0 ? fabs(a) : -fabs(a))	  // for usage in "getrho_ridder"

//////////////////////////////////////////////////////////////////
// constants:

const double UNUSED         = -1.11E30;
const int    MAXIT          = 1000;			// max number of iterations in all mixture-routines
const double RHO_PREC       = 1.0E-8;		// precision for rho in "mixture_getfreeenergy" and "getrho_ridder" = RHO_PREC * rho 
const double BRACKET_PREC   = 1.E-01;	  // bracket width in "getbracketvalues" = RHO_ZERO + BRACKET_PREC * rho (RHO_ZERO from DEFINITS.H) 
const double BRACKET_MINRHO = 1.E-02;  	// min left bracket value in "getbracketvalues" = BRACKET_MINRHO * RHO_ZERO

//////////////////////////////////////////////////////////////////
// routines in LIB-03_TF_MIXTURE.C:

void mixture_getTFquantities( QIPscheme** , Ionpart* , double , double , 
		                          double* , double* , double* , double* , double*, double* );
void mixture_getallquantities( QIPscheme** , Ionpart* , double , double , 
		                           double* , double* , double* , double* , double*, double* );
void mixture_getdpdr_solid( QIPscheme** , Ionpart*,  double* , double* , double*, double* , double* );
int  getbracketvalues( QIPscheme* , double , double , double , double* , double* );
void getrho_Ridder( QIPscheme* , double* , double , double );

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
// eof.