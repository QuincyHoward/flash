//////////////////////////////////////////////////////////////////
// common utility routines 
// used by the FEOS library, the FEOS table generation tool, and by SHOWEOS
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#ifndef COMMON_UTILITIES_H
#define COMMON_UTILITIES_H

//////////////////////////////////////////////////////////////////
// header-files:

#include "COMMON-00_DEFINITS.H"

//////////////////////////////////////////////////////////////////
// routines in COMMON-01_UTILITIES:

void     GetQTABmemory1( Qtable* );
void     GetQTABmemory2( Qtable*, int );
void     FreeQTABmemory( Qtable*, int );
void     GetCTABmemory( CriticalDataTable* );
void     FreeCTABmemory( CriticalDataTable* );
double   Linear_Interpol( double, double,	double, double,	double );
double   *dvector( long, long );
void     free_dvector( double*, long, long );
int*     ivector(long, long);
void     free_ivector(int*, long, long);
float*   vector(long, long );
void     free_vector(float*, long, long );
double** dmatrix( long, long, long, long );
void     delete_dmatrix( double**, long, long, long, long );
double*** dmatrix2( long, long, long, long, long, long );
void     delete_dmatrix2( double***, long, long, long, long, long, long );
float**  matrix( long, long, long, long );
void     delete_matrix( float**, long, long, long, long );
unsigned char **ucmatrix(long, long, long, long );
void     delete_ucmatrix(unsigned char**, long, long, long, long );
int      shift_box( int* , int* , double* , double* , double , double , int , int  );
int      fetch( double* , int , double , double*  );

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
// eof.