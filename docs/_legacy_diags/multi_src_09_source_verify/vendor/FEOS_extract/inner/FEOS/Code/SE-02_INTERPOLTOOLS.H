//////////////////////////////////////////////////////////////////
// service routines for table interpolations 
// used by the SHOWEOS table visualization tool
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#ifndef SE_INTERPOLTOOLS_H
#define SE_INTERPOLTOOLS_H

//////////////////////////////////////////////////////////////////
// header-files:

#include "SE-00_DEFINITS.H"

//////////////////////////////////////////////////////////////////
// routines in SE-02_INTERPOLTOOLS.C:

double fi( Qtable*, Units*, int, double , double , double , double , double );
double get_PQ_LI( double* , double* , double , double , double** , 
		              int , int );
void   polint( double* ,double* ,int ,double ,double* ,double* );
void   polin2( double* ,double* ,double** ,int ,int ,double ,double ,double* ,double* );
void   interpol( double*, double*, double** , double , double , double* ,int , int  );

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
// eof.