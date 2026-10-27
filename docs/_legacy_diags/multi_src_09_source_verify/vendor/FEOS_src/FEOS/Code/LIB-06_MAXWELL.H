//////////////////////////////////////////////////////////////////
// routines for calculation of the Maxwell construction  
// used by the FEOS library
// last change: 2016-07-29
//////////////////////////////////////////////////////////////////

#ifndef LIB_MAXWELL_H
#define LIB_MAXWELL_H 

//////////////////////////////////////////////////////////////////
// header-files:

#include "LIB-00_DEFINITS.H"   
#include "LIB-05_EOS_SERVICES.H"

//////////////////////////////////////////////////////////////////
// constants:

// constants for critical point calculation:
const double epsT = 1.0e-9;                    // precision of critical point data
const double epsR = 1.0e-4;

// constants for Maxwell Construction with equal Gibbs free energy:
const double eps_bisect = 1.0e-8;	           // precision of bisection function

//////////////////////////////////////////////////////////////////
// classes and routines in LIB-06_MAXWELL.C:

class CriticalData {
  public:
    CriticalDataTable data;
    //
    CriticalData( Ionpart* , QIPscheme** , double*, int );
    ~CriticalData();  
  private:
    Ionpart   *ionpart_cd;
    QIPscheme **qipscheme_cd;
    bool      FoundGoodT;
    bool      failure;
    double    *Ttable;
    int       MAXVAP;
    int       Tindexend;
    int       PrintFlag;
    //
    double derivP1( double , double  );
    void   CritPoint();
    double gibbsfreedifference( double , double , 
		                            double*, double*,
		                            double , double,
		                            double, double, double );
    double bisection( double , 
		                  double*,double*, 
		                  double , double ,
		                  double , double  );
    void   vaporisation_curve();
    void   BoilingTemperature();
};

void GetAllMaxwellEOSQuantities( Ionpart* , QIPscheme** , CriticalData*, 
			                           int , int , double , double , int* ,
		 	                           double* , double* , double* , double* , double* , double*,
                                 double* , double* , double* , double* ,
                                 double* , double* , double* , double* ,
                                 double* , double* , double* , double* );

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
// eof.