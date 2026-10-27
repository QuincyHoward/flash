//////////////////////////////////////////////////////////////////
// C/C++ interface routines of the FEOS library 
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#ifndef LIBFEOS
#define LIBFEOS

//////////////////////////////////////////////////////////////////
// routines in LIB-07_C_INTERFACE.C:

#ifdef __cplusplus
extern "C"
{
#endif

void FEOS_Initialize( int, int );
void FEOS_Finalize( );
void FEOS_Get_Calc_Limits( double*, double* );
void FEOS_Init_Mat( int, int, int, int, double*, int, int*, int*, double* );
void FEOS_Delete_Mat( int );
void FEOS_Get_Mat_Par( int, double*, double*, double*, double*, double*, double*,
                       double*, double*, double*, int* );
void FEOS_Get_SoftSphere_Par( int, double*, double*, double*, double*, double* );
void FEOS_Get_Energy_Offsets( int, double*, double* );
void FEOS_Get_Crit_Point( int, double*, double*, double*, double*, double*, double* );
void FEOS_Get_Binodal( int, double*, double*, double*, double*, double*, double*,
                       double*, double*, double*, double*, double*, double*, double* );
void FEOS_Get_Spinodal( int, double*, double*, double*, double*, double* );
void FEOS_Get_EOS_All( int, int, double, double , int*,
			                 double*, double*, double*, double*, double*, double*,
                       double*, double*, double*, double*,
                       double*, double*, double*, double*,
                       double*, double*, double*, double* );
void FEOS_Get_EOS( int, int, int, double, double, int*,
			             double*, double*, double*, double*, double*, double* );
void FEOS_Get_Pmin_Pmax( int, double,
			                   double*, double*, double*, double* );

#ifdef __cplusplus
}
#endif

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
//eof.