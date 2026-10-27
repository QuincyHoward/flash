//////////////////////////////////////////////////////////////////
// routines for reading the material parameter db and calculation of  
// the ionic EOS, the bonding correction, and the soft-sphere function 
// used by the FEOS library
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#ifndef LIB_IONMOD_H 
#define LIB_IONMOD_H

//////////////////////////////////////////////////////////////////
// header-files:

#include "LIB-00_DEFINITS.H"

//////////////////////////////////////////////////////////////////
// classes and routines in LIB-04_IONMOD.C:

class Ionpart {
  public:
    int     MaterialNumber;         // material number from parameter database
    int     SESAMEnumber;
    double  rhosolid, BulkModulus, T_standard;
    int     Nelements;			        // number of elements in the mixture
    double* Aelement;			          // values (A,Z,X) from PAR-file
    double* Zelement;
    double* Xelement_tot;           // X as defined in parameter database
    double* Xelement_frac;			    // number fraction
    double  Amean, AmeanMp, Zmean, Atot, AtotMp, Ztot, Xtot;
    int     PrintFlag;
    int     MaxwellFlag;
    int     SoftSphereFlag;         // replace TF cold curve by soft sphere function for densities < reference density?
    double  E_cohesive, softsphere_m, softsphere_n, softsphere_A, softsphere_B;
    double  rref, gamma_F, gamma_s, kTd, kTm, alpha, deriv_kTd_dr, b_cow, b_bond, Eo_bond, Ei_Offset, Ee_Offset;
    double  f, df, E_zero, p0_bonding, p1_bonding, p2_bonding;
    //
         Ionpart( int, int, int, int );
         ~Ionpart();
    void getBondingParameters( double, double, double, double, double );
    void getEmpiricalModel( double );
    void getIonicQuantities( double, double, double* , double*, double* , double* );
    void get_bonding_contrib( double, double*, double* );
    void getSoftSphereQuantities( double, double*, double* );
  private:
    void get_f_cold_solid(double );
    void get_f_hot_solid(double );
    void get_f_liquid(double, double );
};

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
// eof.