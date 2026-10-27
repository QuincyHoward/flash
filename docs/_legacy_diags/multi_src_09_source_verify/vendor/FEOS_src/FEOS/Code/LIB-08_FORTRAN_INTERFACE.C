//////////////////////////////////////////////////////////////////
// C/C++ interface routines of the FEOS library  
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////
// The fortran interface routines call the C/C++ interface routines.
// All routines are present in two versions to take care of possible
// upper and lower case conversion of Fortran compilers.
// Take care: Depending on your Fortran compiler the "_" sign at the
// end of a routine name normally is added automatically during linking.
//////////////////////////////////////////////////////////////////
        
#include "libfeos.h"  

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_INITIALIZE_( int* entitynumber, int* printflag )
{
  FEOS_Initialize( *entitynumber, *printflag );
  return;  
}
 
extern "C" void feos_initialize_( int* entitynumber, int* printflag )
{
  FEOS_Initialize( *entitynumber, *printflag );
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_FINALIZE_( )
{
  FEOS_Finalize( );
  return; 
}

extern "C" void feos_finalize_( )
{
  FEOS_Finalize( );
  return; 
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_GET_CALC_LIMITS_( double* Tzero, double* Rhozero )
{ 
  FEOS_Get_Calc_Limits( Tzero, Rhozero );
	return;
}

extern "C" void feos_get_calc_limits_( double* Tzero, double* Rhozero )
{ 
  FEOS_Get_Calc_Limits( Tzero, Rhozero );
	return;
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_INIT_MAT_( int* entity, int* materialnumber, int* Maxwellflag, int* softsphereflag, double* MaxwellTtab,  
                                  int* sizeofMaxwellTtab, int* numofelements, int* numofMaxwelliso, double* MaxwellTreliable )
{
  FEOS_Init_Mat( *entity, *materialnumber, *Maxwellflag, *softsphereflag, MaxwellTtab,  
                   *sizeofMaxwellTtab, numofelements, numofMaxwelliso, MaxwellTreliable );
  return;   
}

extern "C" void feos_init_mat_( int* entity, int* materialnumber, int* Maxwellflag, int* softsphereflag, double* MaxwellTtab,  
                                  int* sizeofMaxwellTtab, int* numofelements, int* numofMaxwelliso, double* MaxwellTreliable )
{
  FEOS_Init_Mat( *entity, *materialnumber, *Maxwellflag, *softsphereflag, MaxwellTtab,  
                   *sizeofMaxwellTtab, numofelements, numofMaxwelliso, MaxwellTreliable );
  return;   
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_DELETE_MAT_( int* entity )
{
  FEOS_Delete_Mat( *entity );
  return;  
}

extern "C" void feos_delete_mat_( int* entity )
{
  FEOS_Delete_Mat( *entity );
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_GET_MAT_PAR_( int* entity, double* A, double* Z, double* X, double* Atot, double* Ztot, double* Xtot,                              
                                     double* Tref, double* Rhoref, double* BulkModref, int* SESAMEnumber )
{
  FEOS_Get_Mat_Par( *entity, A, Z, X, Atot, Ztot, Xtot,                              
                      Tref, Rhoref, BulkModref, SESAMEnumber );
  return;  
}

extern "C" void feos_get_mat_par_( int* entity, double* A, double* Z, double* X, double* Atot, double* Ztot, double* Xtot,                              
                                     double* Tref, double* Rhoref, double* BulkModref, int* SESAMEnumber )
{
  FEOS_Get_Mat_Par( *entity, A, Z, X, Atot, Ztot, Xtot,                              
                      Tref, Rhoref, BulkModref, SESAMEnumber );
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_GET_SOFTSPHERE_PAR_( int* entity, double* Ecoh, double* softsp_n, double* softsp_m, double* softsp_A, double* softsp_B  )
{
  FEOS_Get_SoftSphere_Par( *entity, Ecoh, softsp_n, softsp_m, softsp_A, softsp_B );
  return;  
}

extern "C" void feos_get_softsphere_par_( int* entity, double* Ecoh, double* softsp_n, double* softsp_m, double* softsp_A, double* softsp_B  )
{
  FEOS_Get_SoftSphere_Par( *entity, Ecoh, softsp_n, softsp_m, softsp_A, softsp_B );
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_GET_ENERGY_OFFSETS_( int* entity, double* ElectronOffs, double* IonOffs )
{
  FEOS_Get_Energy_Offsets( *entity, ElectronOffs, IonOffs );
  return;  
}

extern "C" void feos_get_energy_offsets_( int* entity, double* ElectronOffs, double* IonOffs )
{
  FEOS_Get_Energy_Offsets( *entity, ElectronOffs, IonOffs );
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_GET_CRIT_POINT_( int* entity, double* T, double* Rho, double* P, double* H, double* S, double* Z )
{
  FEOS_Get_Crit_Point( *entity, T, Rho, P, H, S, Z );
  return;  
}

extern "C" void feos_get_crit_point_( int* entity, double* T, double* Rho, double* P, double* H, double* S, double* Z )
{
  FEOS_Get_Crit_Point( *entity, T, Rho, P, H, S, Z );
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_GET_BINODAL_( int* entity, double* T, double* P, double* Rholiq, double* Rhovap, double* Pliq, double* Pvap, 
                                     double* Gliq, double* Gvap, double* Hliq, double* Hvap, double* Zliq, double* Zvap, double* Tboil )
{
  FEOS_Get_Binodal( *entity, T, P, Rholiq, Rhovap, Pliq, Pvap, 
                      Gliq, Gvap, Hliq, Hvap, Zliq, Zvap, Tboil );
  return;  
}

extern "C" void feos_get_binodal_( int* entity, double* T, double* P, double* Rholiq, double* Rhovap, double* Pliq, double* Pvap, 
                                     double* Gliq, double* Gvap, double* Hliq, double* Hvap, double* Zliq, double* Zvap, double* Tboil )
{
  FEOS_Get_Binodal( *entity, T, P, Rholiq, Rhovap, Pliq, Pvap, 
                      Gliq, Gvap, Hliq, Hvap, Zliq, Zvap, Tboil );
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_GET_SPINODAL_( int* entity, double* T, double* RhoMin, double* RhoMax, double* PMin, double* PMax )
{
  FEOS_Get_Spinodal( *entity, T, RhoMin, RhoMax, PMin, PMax );
  return;  
}

extern "C" void feos_get_spinodal_( int* entity, double* T, double* RhoMin, double* RhoMax, double* PMin, double* PMax )
{
  FEOS_Get_Spinodal( *entity, T, RhoMin, RhoMax, PMin, PMax );
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_GET_EOS_ALL_( int* entity, int* Maxwell, double* Rho, double* T, int* belowbinodal,
			      double* p, double* e, double* s, double* f, double* q, double* qtot,
            double* pe, double* ee, double* se, double* fe, 
            double* pi, double* ei, double* si, double* fi,
            double* pTF, double* eTF, double* sTF, double* fTF )
{ 
  FEOS_Get_EOS_All( *entity, *Maxwell, *Rho, *T, belowbinodal,
			      p, e, s, f, q, qtot,
            pe, ee, se, fe, 
            pi, ei, si, fi,
            pTF, eTF, sTF, fTF );    
  return;
}

extern "C" void feos_get_eos_all_( int* entity, int* Maxwell, double* Rho, double* T, int* belowbinodal,
			      double* p, double* e, double* s, double* f, double* q, double* qtot,
            double* pe, double* ee, double* se, double* fe, 
            double* pi, double* ei, double* si, double* fi,
            double* pTF, double* eTF, double* sTF, double* fTF )
{ 
  FEOS_Get_EOS_All( *entity, *Maxwell, *Rho, *T, belowbinodal,
			      p, e, s, f, q, qtot,
            pe, ee, se, fe, 
            pi, ei, si, fi,
            pTF, eTF, sTF, fTF );    
  return;
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_GET_EOS_( int* entity, int* task, int* Maxwell, double* Rho, double* T, int* belowbinodal,
			                           double* p, double* e, double* s, double* f, double* q, double* qtot )
{
  FEOS_Get_EOS( *entity, *task, *Maxwell, *Rho, *T, belowbinodal,
			            p, e, s, f, q, qtot );
  return;
}

extern "C" void feos_get_eos_( int* entity, int* task, int* Maxwell, double* Rho, double* T, int* belowbinodal,
			                           double* p, double* e, double* s, double* f, double* q, double* qtot )
{
  FEOS_Get_EOS( *entity, *task, *Maxwell, *Rho, *T, belowbinodal,
			            p, e, s, f, q, qtot );
  return;
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_GET_PMIN_PMAX_( int* entity, double* T,
			      double* RhoMin, double* RhoMax, double* PMin, double* PMax )
{
  FEOS_Get_Pmin_Pmax( *entity, *T,
			                  RhoMin, RhoMax, PMin, PMax );
  return;
}

extern "C" void feos_get_pmin_pmax_( int* entity, double* T,
			      double* RhoMin, double* RhoMax, double* PMin, double* PMax )
{
  FEOS_Get_Pmin_Pmax( *entity, *T,
			                  RhoMin, RhoMax, PMin, PMax );
  return;
}

//////////////////////////////////////////////////////////////////
// eof.