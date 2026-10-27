//////////////////////////////////////////////////////////////////
// common utility routines
// used by the FEOS library, the FEOS table generation tool, and by SHOWEOS
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#include "COMMON-01_UTILITIES.H"

//////////////////////////////////////////////////////////////////

void GetQTABmemory1( Qtable* qtab )
{
  int i,j;
  printf( "\nAllocate & reset memory for EOS-table...");

  (*qtab).T = dvector( 0, (*qtab).NT-1 );
  (*qtab).Rho = dvector( 0,(*qtab).NRho-1 );
  (*qtab).P = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).E = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).S = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).F = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).Pe = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).Ee = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).Se = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).Fe = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).Pi = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).Ei = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).Si = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).Fi = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).PTF = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).ETF = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).STF = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  (*qtab).FTF = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  
  // reset:
  for ( i = 0; i < (*qtab).NT; i++) {
    (*qtab).T[i] = 0.0;
  }
  for (i = 0; i < (*qtab).NRho; i++) {
    (*qtab).Rho[i] = 0.0;
    for( j = 0; j < (*qtab).NT; j++) {
      (*qtab).P[i][j] = 0.0;
      (*qtab).E[i][j] = 0.0;
      (*qtab).S[i][j] = 0.0;
      (*qtab).F[i][j] = 0.0;
      (*qtab).Pe[i][j] = 0.0;
      (*qtab).Ee[i][j] = 0.0;
      (*qtab).Se[i][j] = 0.0;
      (*qtab).Fe[i][j] = 0.0;
      (*qtab).Pi[i][j] = 0.0;
      (*qtab).Ei[i][j] = 0.0;
      (*qtab).Si[i][j] = 0.0;
      (*qtab).Fi[i][j] = 0.0;
      (*qtab).PTF[i][j] = 0.0;
      (*qtab).ETF[i][j] = 0.0;
      (*qtab).STF[i][j] = 0.0;
      (*qtab).FTF[i][j] = 0.0;
    }
  }
  
  printf(" done.\n");
  return;
}

//////////////////////////////////////////////////////////////////

void GetQTABmemory2( Qtable* qtab, int ordering )
{
  int i,j,k;
  printf( "\nAllocate & reset memory for EOS parameters / charge state...");
  
  (*qtab).A = dvector( 0, (*qtab).Nelements-1 );
  (*qtab).Z = dvector( 0, (*qtab).Nelements-1 );
  (*qtab).X = dvector( 0, (*qtab).Nelements-1 );
  (*qtab).Qtot = dmatrix(0,(*qtab).NRho-1,0,(*qtab).NT-1);
  if(ordering) (*qtab).Q = dmatrix2(0,(*qtab).Nelements-1,0,(*qtab).NRho-1,0,(*qtab).NT-1); 
  else (*qtab).Q = dmatrix2(0,(*qtab).NRho-1,0,(*qtab).NT-1,0,(*qtab).Nelements-1);  
  
  for(k=0; k<(*qtab).Nelements; k++) {
    (*qtab).A[k] = 0.0;
    (*qtab).Z[k] = 0.0;
    (*qtab).X[k] = 0.0;    
  }
  for (i = 0; i < (*qtab).NRho; i++) {
    for( j = 0; j < (*qtab).NT; j++) {
      (*qtab).Qtot[i][j] = 0.0;
      for( k = 0; k < (*qtab).Nelements; k++) {
        if (ordering) (*qtab).Q[k][i][j] = 0.0; 
        else (*qtab).Q[i][j][k] = 0.0; 
      }
    }
  }        
  
  printf(" done.\n");
  return;
}

//////////////////////////////////////////////////////////////////

void FreeQTABmemory( Qtable* qtab, int ordering )
{
  free_dvector((*qtab).T,0,(*qtab).NT-1);
  free_dvector((*qtab).Rho,0,(*qtab).NRho-1);
  delete_dmatrix((*qtab).P,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).E,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).S,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).F,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).Pe,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).Ee,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).Se,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).Fe,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).Pi,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).Ei,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).Si,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).Fi,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).PTF,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).ETF,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).STF,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  delete_dmatrix((*qtab).FTF,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  free_dvector((*qtab).A,0,(*qtab).Nelements-1);
  free_dvector((*qtab).Z,0,(*qtab).Nelements-1);
  free_dvector((*qtab).X,0,(*qtab).Nelements-1);
  delete_dmatrix((*qtab).Qtot,0,(*qtab).NRho-1,0,(*qtab).NT-1);
  if(ordering) delete_dmatrix2((*qtab).Q,0,(*qtab).Nelements-1,0,(*qtab).NRho-1,0,(*qtab).NT-1); 
  else delete_dmatrix2((*qtab).Q,0,(*qtab).NRho-1,0,(*qtab).NT-1,0,(*qtab).Nelements-1);
  return;
}
//////////////////////////////////////////////////////////////////

void GetCTABmemory( CriticalDataTable* ctab )
{
  int k;
  printf( "\nAllocate & reset memory for critical-data table...");

  (*ctab).Rhoc = (*ctab).Pc = (*ctab).Tc = (*ctab).Hc = (*ctab).Zc = (*ctab).Sc = (*ctab).Tb = 0.0;
  
  (*ctab).Rhol = dvector(0,(*ctab).Niso-1);
  (*ctab).Rhov = dvector(0,(*ctab).Niso-1);
  (*ctab).Pl = dvector(0,(*ctab).Niso-1);
  (*ctab).Pv = dvector(0,(*ctab).Niso-1);
  (*ctab).Peq = dvector(0,(*ctab).Niso-1);
  (*ctab).Tiso = dvector(0,(*ctab).Niso-1);
  (*ctab).Rhomax = dvector(0,(*ctab).Niso-1);
  (*ctab).Rhomin = dvector(0,(*ctab).Niso-1);
  (*ctab).Pmin = dvector(0,(*ctab).Niso-1);
  (*ctab).Pmax = dvector(0,(*ctab).Niso-1);
  (*ctab).Gl = dvector(0,(*ctab).Niso-1);
  (*ctab).Gv = dvector(0,(*ctab).Niso-1);
  (*ctab).Hl = dvector(0,(*ctab).Niso-1);
  (*ctab).Hv = dvector(0,(*ctab).Niso-1);
  (*ctab).Zl = dvector(0,(*ctab).Niso-1);
  (*ctab).Zv = dvector(0,(*ctab).Niso-1);
  
  for (k = 0; k < (*ctab).Niso; k++) {
    (*ctab).Rhol[k] = 0.0;
    (*ctab).Rhov[k] = 0.0;
    (*ctab).Pl[k] = 0.0;
    (*ctab).Pv[k] = 0.0;
    (*ctab).Peq[k] = 0.0;
    (*ctab).Tiso[k] = 0.0;
    (*ctab).Rhomax[k] = 0.0;
    (*ctab).Rhomin[k] = 0.0;
    (*ctab).Pmin[k] = 0.0;
    (*ctab).Pmax[k] = 0.0;
    (*ctab).Gl[k] = 0.0;
    (*ctab).Gv[k] = 0.0;
    (*ctab).Hl[k] = 0.0;
    (*ctab).Hv[k] = 0.0;
    (*ctab).Zl[k] = 0.0;
    (*ctab).Zv[k] = 0.0;
  }
  
  printf(" done.\n");
  return;
}

//////////////////////////////////////////////////////////////////

void FreeCTABmemory( CriticalDataTable* ctab )
{
  free_dvector((*ctab).Rhol,0,(*ctab).Niso-1);
  free_dvector((*ctab).Rhov,0,(*ctab).Niso-1);
  free_dvector((*ctab).Pl,0,(*ctab).Niso-1);
  free_dvector((*ctab).Pv,0,(*ctab).Niso-1);
  free_dvector((*ctab).Peq,0,(*ctab).Niso-1);
  free_dvector((*ctab).Tiso,0,(*ctab).Niso-1);
  free_dvector((*ctab).Rhomax,0,(*ctab).Niso-1);
  free_dvector((*ctab).Rhomin,0,(*ctab).Niso-1);
  free_dvector((*ctab).Pmin,0,(*ctab).Niso-1);
  free_dvector((*ctab).Pmax,0,(*ctab).Niso-1);
  free_dvector((*ctab).Gl,0,(*ctab).Niso-1);
  free_dvector((*ctab).Gv,0,(*ctab).Niso-1);
  free_dvector((*ctab).Hl,0,(*ctab).Niso-1);
  free_dvector((*ctab).Hv,0,(*ctab).Niso-1);
  free_dvector((*ctab).Zl,0,(*ctab).Niso-1);
  free_dvector((*ctab).Zv,0,(*ctab).Niso-1);
  return;
}

//////////////////////////////////////////////////////////////////

double Linear_Interpol( double x0, double x1, 
			double y0, double y1, 
			double x )
{
  return y0 + (y1-y0)*(x-x0)/(x1-x0);
}

//////////////////////////////////////////////////////////////////

double *dvector(long nl, long nh)
{
  // allocate a double vector with subscript range v[nl..nh]
  
  double *v;

  v=(double *)malloc((size_t) ((nh-nl+1+N_END)*sizeof(double)));
  if (!v) printf("\nCOMMON-ERROR in dvector ---> Allocation error !!!\n");
  return v-nl+N_END;
}

//////////////////////////////////////////////////////////////////

void free_dvector(double *v, long nl, long nh)
{
  // free a double vector allocated with dvector()
  
  free((FREE_ARG) (v+nl-N_END));
}

//////////////////////////////////////////////////////////////////

int *ivector(long nl, long nh)
{
  // allocate an int vector with subscript range v[nl..nh]
  
  int *v;
  
  v=(int *)malloc((size_t) ((nh-nl+1+N_END)*sizeof(int)));
  if (!v) printf("\nCOMMON-ERROR in ivector ---> Allocation error !!!\n");
  return v-nl+N_END;
}

//////////////////////////////////////////////////////////////////

void free_ivector(int *v, long nl, long nh)
{
  // free an int vector allocated with ivector()
  
  free((FREE_ARG) (v+nl-N_END));
}

//////////////////////////////////////////////////////////////////

float *vector(long nl, long nh)
{
  // allocate a float vector with subscript range v[nl..nh]
  
  float *v;

  v=(float *)malloc((size_t) ((nh-nl+1+N_END)*sizeof(float)));
  if (!v) printf("\nCOMMON-ERROR in vector ---> Allocation error !!!\n");
  return v-nl+N_END;
}

//////////////////////////////////////////////////////////////////

void free_vector(float *v, long nl, long nh) 
{
  // free a float vector allocated with vector()
  
  free((FREE_ARG) (v+nl-N_END));
}

//////////////////////////////////////////////////////////////////

double **dmatrix(long nrl, long nrh, long ncl, long nch)
{
  // allocate a double matrix with subscript range m[nrl..nrh][ncl..nch]
   
  long i, nrow=nrh-nrl+1, ncol=nch-ncl+1;
  double **m;

  // allocate pointers to rows 
  m=(double **) malloc((size_t)((nrow+N_END)*sizeof(double*)));
  if (!m) printf("\nCOMMON-ERROR in dmatrix ---> Allocation error 1 !!!\n");
  m += N_END;
  m -= nrl;

  // allocate rows and set pointers to them 
  m[nrl]=(double *) malloc((size_t)((nrow*ncol+N_END)*sizeof(double)));
  if (!m[nrl]) printf("\nCOMMON-ERROR in dmatrix ---> Allocation error 2 !!!\n");
  m[nrl]+=N_END;
  m[nrl]-=ncl;

  for(i=nrl+1;i<=nrh;i++) m[i]=m[i-1]+ncol;

  // return pointer to array of pointers to rows 
  return m;
}

//////////////////////////////////////////////////////////////////

void delete_dmatrix( double **m, long nrl, long nrh, long ncl, long nch) 
{
  // free a double matrix allocated by dmatrix()
  
  free((FREE_ARG) (m[nrl]+ncl-N_END));
  free((FREE_ARG) (m+nrl-N_END));
}

//////////////////////////////////////////////////////////////////

double ***dmatrix2(long nrl, long nrh, long ncl, long nch, long ncl2, long nch2)
{
  // allocate a double matrix with subscript range m[nrl..nrh][ncl..nch][ncl2..nch2]
  
  long i, j, nrow=nrh-nrl+1, ncol=nch-ncl+1, ncol2=nch2-ncl2+1;
  double ***m;

  // allocate pointers to rows 
  m=(double ***) malloc((size_t)((nrow+N_END)*sizeof(double**)));
  if (!m) printf("\nCOMMON-ERROR in dmatrix2 ---> Allocation error 1 !!!\n");
  m += N_END;
  m -= nrl;

  // allocate rows and set pointers to cols
  m[nrl]=(double **) malloc((size_t)((nrow*ncol+N_END)*sizeof(double*)));
  if (!m[nrl]) printf("\nCOMMON-ERROR in dmatrix2 ---> Allocation error 2 !!!\n");
  m[nrl]+=N_END;
  m[nrl]-=ncl;
  for(i=nrl+1;i<=nrh;i++) m[i]=m[i-1]+ncol;

  // allocate cols and set pointers to them 
  for(i=nrl;i<=nrh;i++) {
    m[i][ncl]=(double *) malloc((size_t)((ncol*ncol2+N_END)*sizeof(double)));
    if (!m[i][ncl]) printf("\nCOMMON-ERROR in dmatrix ---> Allocation error 3 !!!\n");
    m[i][ncl]+=N_END;
    m[i][ncl]-=ncl2;
    for(j=ncl+1;j<=nch;j++) m[i][j]=m[i][j-1]+ncol2;
  }
  
  // return pointer to array of pointers to rows 
  return m;
}

//////////////////////////////////////////////////////////////////

void delete_dmatrix2( double ***m, long nrl, long nrh, long ncl, long nch, long ncl2, long nch2) 
{
  // free a double matrix allocated by dmatrix2()
  
  int i;
  for(i=nrl;i<=nrh;i++) free((FREE_ARG) (m[i][ncl]+ncl2-N_END));
  free((FREE_ARG) (m[nrl]+ncl-N_END));
  free((FREE_ARG) (m+nrl-N_END));
}

//////////////////////////////////////////////////////////////////

float **matrix(long nrl, long nrh, long ncl, long nch)
{
  // allocate a float matrix with subscript range m[nrl..nrh][ncl..nch]
   
  long i, nrow=nrh-nrl+1, ncol=nch-ncl+1;
  float **m;

  // allocate pointers to rows 
  m=(float **) malloc((size_t)((nrow+N_END)*sizeof(float*)));
  if (!m) printf("\nCOMMON-ERROR in matrix ---> Allocation error 1 !!!\n");
  
  // allocate rows and set pointers to them 
  m[nrl]=(float *) malloc((size_t)((nrow*ncol+N_END)*sizeof(float)));
  if (!m[nrl]) printf("\nCOMMON-ERROR in matrix ---> Allocation error 1 !!!\n");
  m[nrl]+=N_END;
  m[nrl]-=ncl;

  for(i=nrl+1;i<=nrh;i++) m[i]=m[i-1]+ncol;

  // return pointer to array of pointers to rows 
  return m;
}

//////////////////////////////////////////////////////////////////

void delete_matrix( float **m, long nrl, long nrh, long ncl, long nch)
{
  // free a float matrix allocated by matrix()
   
  free((FREE_ARG) (m[nrl]+ncl-N_END));
  free((FREE_ARG) (m+nrl-N_END));
}

//////////////////////////////////////////////////////////////////

unsigned char **ucmatrix(long nrl, long nrh, long ncl, long nch)
{
  // allocate a unsigned char matrix with subscript range m[nrl..nrh][ncl..nch]
  
  long i, nrow=nrh-nrl+1, ncol=nch-ncl+1;
  unsigned char **m;

  // allocate pointers to rows
  m=(unsigned char **) malloc((size_t)((nrow+N_END)*sizeof(unsigned char*)));
  if (!m) printf("\nCOMMON-ERROR in ucmatrix ---> Allocation error 1 !!!\n");
  
  // allocate rows and set pointers to them
  m[nrl]=(unsigned char *) malloc((size_t)((nrow*ncol+N_END)*sizeof(unsigned char)));
  if (!m[nrl]) printf("\nCOMMON-ERROR in ucmatrix ---> Allocation error 2 !!!\n");
  m[nrl]+=N_END;
  m[nrl]-=ncl;

  for(i=nrl+1;i<=nrh;i++) m[i]=m[i-1]+ncol;

  // return pointer to array of pointers to rows
  return m;
}

//////////////////////////////////////////////////////////////////

void free_ucmatrix( unsigned char **m, long nrl, long nrh, long ncl, long nch)
{
  // free a unsigned char matrix allocated by ucmatrix()
  
  free((FREE_ARG) (m[nrl]+ncl-N_END));
  free((FREE_ARG) (m+nrl-N_END));
}

////////////////////////////////////////////////////////////////////////

int shift_box( int* i, int* j, double* x1_field, double* x2_field, 
		double x1, double x2, int imax, int jmax )
{
  // go to lower-left box corner index of the box containing (x1,x2)
  // return 0  if in table
  //        1  if t<t min
  //        -1 else.

  if( x1_field[*i]-x1 > -0.0 ) *i = 1; 
  while( ( *i < imax ) && (x1_field[*i]-x1)*(x1_field[*i+1]-x1) > -0.0 ) (*i)++; 

  if( x2_field[*j]-x2 > -0.0 ) *j = 1;
  while( ( *j < jmax ) && (x2_field[*j]-x2)*(x2_field[*j+1]-x2) > -0.0 ) (*j)++;

  if( *i==imax || *j==jmax ) {
    if( *i<imax && x2<x2_field[1] ) { *j = 1; return 1; }                      // t - > 0 extrapolation
    else if( *i<imax && x2>x2_field[jmax] ) { *j = jmax; return 2; }           // t -> oo extrapolation
    else if( *j<jmax && x1<x1_field[1] ) { *i = 1; return 3; }                 // u - > 0 extrap
    else if( *j<jmax && x1>x1_field[imax] ) { *i = imax; return 4; }           // u -> oo extrap
    else if( x1<x1_field[1] && x2<x2_field[1] ) { *i = (*j) = 1; return 5; }
    else if( x1<x1_field[1] && x2>x2_field[jmax] ) { *i = 1; *j = jmax; return 6; }  
    else if( x1>x1_field[imax] && x2>x2_field[jmax] ) { *i = imax; *j = jmax; return 7; }
    else if( x1>x1_field[jmax] && x2<x2_field[1] ) { *i = imax; *j = 1; return 8; }
    else return -1;
  } 
  else return 0;
}

//////////////////////////////////////////////////////////////////////////

int fetch( double* vec, int imax, double v, double* dev ) 
{
  // return index of element closest to v, but smaller than v
  
  int i, 
      is = -1;
  double dnew;

  *dev = 1e99;
  for(i=1;i<=imax;i++) 
    if( (dnew=fabs(vec[i] - v)) <= *dev ) { *dev = dnew; is = i; }
  
  if( vec[is] > v) is--;
  if (is<0) {
    printf("\nCOMMON-ERROR in fetch ---> Out of range in table at = %e !!!\n",v);
    exit(0);
  }
  return is;
}
  
//////////////////////////////////////////////////////////////////  
// eof.