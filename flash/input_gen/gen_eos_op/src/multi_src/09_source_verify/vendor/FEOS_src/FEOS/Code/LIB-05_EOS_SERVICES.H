//////////////////////////////////////////////////////////////////
// routines to get thermodynamic functions without Maxwell construction  
// used by the FEOS library
// last change: 2016-07-29
//////////////////////////////////////////////////////////////////

#ifndef LIB_EOS_SERVICES_H
#define LIB_EOS_SERVICES_H 

//////////////////////////////////////////////////////////////////
// header-files:

#include "LIB-00_DEFINITS.H" 
#include "LIB-03_TF_MIXTURE.H"  

//////////////////////////////////////////////////////////////////
// constants:

const double NOTCALCULATED_QUANTITY  = -1.0e60;   // return value for uncalculated quantities
const double CONTAINS_LOOP_PREC_R    = 0.05;      // important parameter for precision of loop and critical point finding, set not higher than 0.5
const double CONTAINS_LOOP_NUM_NOISE = 1.0;		    // set this factor 1.01 if you experience numerical trouble finding loops
const double START_R_GETPMAX         = 1.0e-10;   // starting density for finding maximum pressure
const double START_R_GETPMIN         = 1.0e4;     // starting density for finding minimum pressure
const double DELTA_R_GETPMAXPMIN     = 0.01;      // precision for finding maximum and minimum pressure
const double eps_getR                = 1.0e-8;	  // precision of bisection function for getting R(P)

//////////////////////////////////////////////////////////////////
// routines in LIB-05_EOS_SERVICES.C:

void   GetElectronEOSQuantities( Ionpart* , QIPscheme** , int ,
                                 double , double ,
		 	                           double* , double* , double* , double* , double* , double*,
                                 double* , double* , double* , double* );
void   GetIonEOSQuantities( Ionpart* , QIPscheme** , 
			                      double , double ,
		 	                      double* , double* , double* , double* );		 	
void   GetAllEOSQuantities( Ionpart* , QIPscheme** , int ,
			                      double , double ,
		 	                      double* , double* , double* , double* , double* , double*,
                            double* , double* , double* , double* ,
                            double* , double* , double* , double* ,
                            double* , double* , double* , double* );
void   GetTotalEOSQuantities( Ionpart* , QIPscheme** ,
			                        double , double ,
		 	                        double* , double* , double* , double* , double* , double* );
void   getPmax_Pmin( Ionpart*, QIPscheme**, double,
                     double*, double*, double*, double*, int ); 
int    contains_loop( Ionpart*, QIPscheme**, double, double );
double getRofP( Ionpart*, QIPscheme**, double, double, double, double, bool*, int );

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
// eof.