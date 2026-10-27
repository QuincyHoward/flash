//////////////////////////////////////////////////////////////////
// routines for calculation of the single element Thomas-Fermi EOS
// part 1 of 2
// used by the FEOS library
// last change: 2013-07-01
////////////////////////////////////////////////////////////////// 
// Bikubische Interpolation mit xlogx anstelle des kubischen Terms
// daten fuer das Array aus mathematica/gmat.tex
// completely in cgs units !
// for t - > 0 and for u -> 0 final values used.
////////////////////////////////////////////////////////////////// 

#include "LIB-02_TF_TABLE.H"

////////////////////////////////////////////////////////////////// 

void QIPscheme::Qextrapolate_u0( double* y, double* y1, double* y2, double* y12,
				 double x1l, double x2l, double x2u,
				 double x1, double x2,
				 double* ansy, double* ansy1, double* ansy2 )
{
  int i;
	double t,u,tlogt,logtp1;
	double **c;
	
	c = dmatrix( 1,2,1,4 );
	//  x1l = 1.0; 
	//  x2l = 1.0e8;// !!!! 
	
	Qextra_8cof( y,y1,y2,y12,x1l,x2l,c,3 );
	u = x1 / x1l;
	t = x2 / x2l;
	tlogt  = t*log(t);
	logtp1 = log(t) + 1.0;
	*ansy = (*ansy1) = (*ansy2) = 0.0;
	for( i=2;i>=1;i-- ) {    
	  *ansy  = u * (*ansy) + u * ( c[i][1] + c[i][2]*t+c[i][3]*t*t + 
	    c[i][4]*tlogt );
    *ansy1 = 2.0*u*(*ansy1) +  ( c[i][1] + c[i][2]*t+c[i][3]*t*t + 
      c[i][4]*tlogt );
    *ansy2 = u* (*ansy2) + u * ( c[i][2] + c[i][3]*2.0*t + c[i][4]* logtp1 );
  }
  //    printf("1:%e %e %e %e\n",c[1][1],c[1][2],c[1][3],c[1][4] );
  //    printf("2:%e %e %e %e\n",c[2][1],c[2][2],c[2][3],c[2][4] );
  (*ansy1) /= x1l;
  (*ansy2) /= x2l;
  delete_dmatrix( c, 1,2,1,4 );
  return;
}

////////////////////////////////////////////////////////////////// 

void QIPscheme::Qextrapolate_u_inf( double* y, double* y1, double* y2, double* y12,
         double x1u, double x2l, double x2u,
         double x1, double x2,
         double* ansy, double* ansy1, double* ansy2 )
{
  int i;
  double t,u,tlogt,logtp1,logu,logup1;
  double **c;
  c = dmatrix( 1,2,1,4 );
  Qextra_8cof( y,y1,y2,y12,x1u,x2l,c,4 );

  u = x1 / x1u;
  t = x2 / x2l;
  tlogt  = t*log(t);
  logtp1 = log(t) + 1.0;
  logu = log(u);
  logup1 = logu + 1.0;

  *ansy = (*ansy1) = (*ansy2) = 0.0;
  for( i=2;i>=1;i-- ) {
    *ansy  = logu * (*ansy) + u * ( c[i][1] + c[i][2]*t+c[i][3]*t*t + 
        c[i][4]*tlogt );
    *ansy1 = logup1 * (*ansy1) +  ( c[i][1] + c[i][2]*t+c[i][3]*t*t + 
        c[i][4]*tlogt );
    *ansy2 = logu* (*ansy2) + u * ( c[i][2] + c[i][3]*2.0*t + c[i][4]* logtp1 );
  }
  *ansy1 /= x1u;
  *ansy2 /= x2l;
  delete_dmatrix( c, 1,2,1,4 );
  return;
}

////////////////////////////////////////////////////////////////// 

void QIPscheme::Qextrapolate_t0( double* y,double* y1,double* y2,double* y12,
        double x1l,double x1u,double x2l,
        double x1,double x2,
        double* ansy,double* ansy1, double* ansy2)
{
  int i;

  double t,u,**c,
    ulogu,logup1;
  c = dmatrix(1,2,1,4);
  Qextra_8cof(y,y1,y2,y12,x1l,x2l,c ,1);

  u = x1 / x1l;
  t = x2 / x2l;
  ulogu = u *log(u);
  logup1 = log(u)+1.0;
  *ansy=(*ansy2)=(*ansy1)=0.0;
  for (i=2;i>=1;i--) {
    *ansy  = t*t*(*ansy)+ c[i][4]*ulogu +c[i][3]*u*u+c[i][2]*u+c[i][1];
    *ansy1 = t*t * (*ansy1) + 2.0*c[i][3]*u + c[i][2] + logup1*c[i][4];
   }
   *ansy2 =  2.0 * t * ( c[2][1] + c[2][2]*u + c[2][3]*u*u + ulogu*c[2][4] ); 

  
  *ansy1 /= x1l;
  *ansy2 /= x2l;
  delete_dmatrix(c, 1,2,1,4);
  return;
}

////////////////////////////////////////////////////////////////// 

void QIPscheme::Qextrapolate_t_inf(double* y,double* y1,double* y2,double* y12,
        double x1l,double x1u,double x2u,
        double x1,double x2,
        double* ansy,double* ansy1, double* ansy2)
{
  int i;
  double t,u,**c,
    ulogu,logup1;
  c = dmatrix(1,2,1,4);
  Qextra_8cof(y,y1,y2,y12,x1l,x2u,c, 2 );

  u = x1 / x1l;
  t = x2 / x2u;
  ulogu = u *log(u);
  logup1 = log(u)+1.0;
  *ansy=(*ansy2)=(*ansy1)=0.0;
  for (i=2;i>=1;i--) {
    *ansy  = t * (*ansy)+ c[i][4]*ulogu +c[i][3]*u*u+c[i][2]*u+c[i][1];
    *ansy1 = t * (*ansy1) + 2.0*c[i][3]*u + c[i][2] + logup1*c[i][4];
  }
  *ansy2 =  c[2][1] + c[2][2]*u + c[2][3]*u*u + c[2][4]* ulogu;
  
  *ansy1 /= x1l;
  *ansy2 /= x2u;
  delete_dmatrix(c, 1,2,1,4);
  return;
}

////////////////////////////////////////////////////////////////// 

void QIPscheme::Qextrapolate_u0t0(double* y,double* y1,double* y2,double* y12,
        double x1l,double x2l,
        double x1,double x2,
        double* ansy,double* ansy1, double* ansy2)
{
  int i;
  double t,u,**c;
  c = dmatrix(1,2,1,2);
  Qextra_4cof(y,y1,y2,y12,x1l,x2l,c, 5 );

  u = x1 / x1l;
  t = x2 / x2l;

  *ansy=(*ansy2)=(*ansy1)=0.0;
  for (i=2;i>=1;i--) {
    *ansy  = u*(*ansy)+ c[i][1]*u +c[i][2]*u*t*t;
    *ansy1 = 2.0*u* (*ansy1) + c[i][1] + c[i][2]*t*t;
   }
   *ansy2 =  2.0*t* ( c[1][2]*u + c[2][2]*u*u );
  
  *ansy1 /= x1l;
  *ansy2 /= x2l;
  delete_dmatrix(c, 1,2,1,2);
  return;
}

////////////////////////////////////////////////////////////////// 

void QIPscheme::Qextrapolate_u0tinf(double* y,double* y1,double* y2,double* y12,
        double x1l,double x2u,
        double x1,double x2,
        double* ansy,double* ansy1, double* ansy2)
{
  int i;
  double t,u,**c;
  c = dmatrix(1,2,1,2);
  Qextra_4cof(y,y1,y2,y12,x1l,x2u,c, 6 );

  u = x1 / x1l;
  t = x2 / x2u;

  *ansy=(*ansy2)=(*ansy1)=0.0;
  for (i=2;i>=1;i--) {
    *ansy  = u*(*ansy)+ c[i][1]*u +c[i][2]*u*t;
    *ansy1 = 2.0*u* (*ansy1) + c[i][1] + c[i][2]*t;
   }
   *ansy2 =  ( c[1][2]*u + c[2][2]*u*u );
  
  *ansy1 /= x1l;
  *ansy2 /= x2u;
  delete_dmatrix(c, 1,2,1,2);
  return;
}

////////////////////////////////////////////////////////////////// 

void QIPscheme::Qextrapolate_uinftinf(double* y,double* y1,double* y2,double* y12,
        double x1u,double x2u,
        double x1,double x2,
        double* ansy,double* ansy1, double* ansy2)
{
  int i;
  double t,u,**c,
    ulogu,logu,logup1;
  c = dmatrix(1,2,1,2);
  Qextra_4cof(y,y1,y2,y12,x1u,x2u,c, 7 );

  u = x1 / x1u;
  t = x2 / x2u;
  logu = log(u);
  ulogu = u *log(u);
  logup1 = log(u)+1.0;
  *ansy=(*ansy2)=(*ansy1)=0.0;
  for (i=2;i>=1;i--) {
    *ansy  = logu*(*ansy)+ c[i][1]*u +c[i][2]*u*t;
    *ansy1 = logup1* (*ansy1) + c[i][1] + c[i][2]*t;
   }
   *ansy2 =  ( c[1][2]*u + c[2][2]*ulogu );
  
  *ansy1 /= x1u;
  *ansy2 /= x2u;
  delete_dmatrix(c, 1,2,1,2);
  return;
}

////////////////////////////////////////////////////////////////// 

void QIPscheme::Qextrapolate_uinft0(double* y,double* y1,double* y2,double* y12,
        double x1u,double x2l,
        double x1,double x2,
        double* ansy,double* ansy1, double* ansy2)
{
  int i;
  double t,u,**c,
    ulogu,logu,
    logup1;
  c = dmatrix(1,2,1,2);
  Qextra_4cof(y,y1,y2,y12,x1u,x2l,c, 8 );

  u = x1 / x1u;
  t = x2 / x2l;
  //printf(" u t = %e %e\n",u,t );
  logu = log(u);
  ulogu = u *log(u);
  logup1 = log(u)+1.0;
  //  c[2][1] = 0.0;
  *ansy=(*ansy2)=(*ansy1)=0.0;
  for (i=2;i>=1;i--) {
    *ansy  = logu*(*ansy)+ c[i][1]*u +c[i][2]*u*t*t;
    *ansy1 = logup1* (*ansy1) + c[i][1] + c[i][2]*t*t;
   }
   *ansy2 = 2.0*t* ( c[1][2]*u + c[2][2]*ulogu );
  //printf(" an1 = %e an2 = %e x1u = %e x2l = %e\n",*ansy1, *ansy2, x1u, x2l );
  //printf( "der Koeff D 0 = %e\n",c[2][1] );
  *ansy1 /= x1u;
  *ansy2 /= x2l;
  delete_dmatrix(c, 1,2,1,2);
  return;
}

////////////////////////////////////////////////////////////////// 

void QIPscheme::bcucof(double* y,double* y1,double* y2,double* y12,double d1,double d2,double** c)
{  
  int l,k,j,i;
  double xx,d1d2,cl[16],x[16];

  d1d2=d1*d2;
  for (i=1;i<=4;i++) {
    x[i-1]=y[i];
    x[i+3]=y1[i]*d1;
    x[i+7]=y2[i]*d2;
    x[i+11]=y12[i]*d1d2;
  }
  for (i=0;i<=15;i++) {
    xx=0.0;
    for (k=0;k<=15;k++) xx += wtN[i][k]*x[k];
    cl[i]=xx;
  }
  l=0;
  for (i=1;i<=4;i++)
    for (j=1;j<=4;j++) c[i][j]=cl[l++];
  return;
}

//////////////////////////////////////////////////////////////////

void QIPscheme::bcuint(double* y,double* y1,double* y2,double* y12,
      double x1l,double x1u,double x2l,double x2u,
      double x1,double x2,double* ansy,double* ansy1, double* ansy2)
{
  int i;
  double t,u,d1,d2,**c;
  c=dmatrix(1,4,1,4);
  d1=x1u-x1l;
  d2=x2u-x2l;
  bcucof(y,y1,y2,y12,d1,d2,c);
  if (PrintFlag && (x1u == x1l || x2u == x2l)) printf("\nWARNING from QIPscheme::bcuint ---> Bad input in BCUINT !\n");
  t=(x1-x1l)/d1;
  u=(x2-x2l)/d2;
  *ansy=(*ansy2)=(*ansy1)=0.0;
  for (i=4;i>=1;i--) {
    *ansy=t*(*ansy)+((c[i][4]*u+c[i][3])*u+c[i][2])*u+c[i][1];
    *ansy2=t*(*ansy2)+(3.0*c[i][4]*u+2.0*c[i][3])*u+c[i][2];
    *ansy1=u*(*ansy1)+(3.0*c[4][i]*t+2.0*c[3][i])*t+c[2][i];
  }
  *ansy1 /= d1;
  *ansy2 /= d2;
  delete_dmatrix(c,1,4,1,4);
  return;
}

//////////////////////////////////////////////////////////////////

HTable::HTable( char*  name_in, int printflag )
{
  PrintFlag = printflag;
  generate3( name_in );
}

//////////////////////////////////////////////////////////////////

void HTable::generate3( char* t1_path )  
{
  // offset = 1. indices start with zero
  // read TF table ( without scaling ) and convert in into a H-table.
  // no cold data.
  // H given in cgs units
  // delete TF table out of memory afterwards
  
  int i,j,ki;
  double rho;
  TFtable tft1;
  int CUT = 1;
 
  read_TF_TABLE( t1_path, &tft1, PrintFlag );
  //  write_TF_TABLE( "cippa", &tft1, PrintFlag );
  if(PrintFlag) printf("  Generate H table..." );
  NU = tft1.NR;
  NT = tft1.NT-CUT;           

  ufield = dvector(1,NU);
  Tfield = dvector(1,NT);
  Hfield   = dmatrix(1,NU,1,NT); 
  H1field  = dmatrix(1,NU,1,NT); 
  H2field  = dmatrix(1,NU,1,NT); 
  H12field = dmatrix(1,NU,1,NT);
  Qfield   = dmatrix(1,NU,1,NT);

  TabMult_rho = tft1.rho[2]/tft1.rho[1];  // store table properties
  TabMult_T   = tft1.Te[3]/tft1.Te[2];  
  for( i=1; i<=NU; i++ ) ufield[i] = pow( tft1.rho[NU+1-i], -ZWEI_DRITTEL ); 
  // correct order
  for( j=1; j<=NT; j++ ) Tfield[j] = eV2cgs*tft1.Te[j+CUT]; // no cold data, in cgs units
 
  for(i=1;i<=NU;i++) {
    ki = NU+1-i;  
    for(j=1;j<=NT;j++) {
      rho = pow( ufield[i],-1.5 );
      Hfield[i][j]   =   ufield[i] * ( tft1.Fe[ki][j+CUT] );
      H1field[i][j]  =   ( tft1.Fe[ki][j+CUT]  )   - 1.5 * tft1.Pe[ki][j+CUT] / rho; 
      H2field[i][j]  = - ufield[i]               *  tft1.Se[ki][j+CUT];
      H12field[i][j] = - tft1.Se[ki][j+CUT] -( 1.5 * tft1.dPdT[ki][j+CUT]/rho ) / eV2cgs;
      Qfield[i][j]   =   tft1.Q[ki][j+CUT];
    }
  }
  clear_TF_TABLE( &tft1 );
  if(PrintFlag) printf(" done.\n");
  return;
}

//////////////////////////////////////////////////////////////////

void HTable::write( char* name )
{
  FILE* h;
  int i,j,c;
  if(PrintFlag) printf("Write H table to file %s\n", name);
  h = fopen(name,"w");
  fprintf(h,"%d  %d\n",NU,NT );
  c=1;
  for(i=1;i<=NU;i++,c++) {
    if(c>1) fprintf(h,"  ");
    fprintf(h,"%e",ufield[i]); 
    if(c==5){c=0;fprintf(h,"\n");} 
  }
  c=1;
  for(j=1;j<=NT;j++,c++) {
    if(c>1) fprintf(h,"  ");
    fprintf(h,"%e",Tfield[j]); 
    if(c==5) {c=0;fprintf(h,"\n");} 
  }
  fprintf(h,"\n");
  for(i=1;i<=NU;i++) 
    for(j=1;j<=NT;j++ )  
      fprintf(h,"%e  %e  %e  %e  %e\n",
        Hfield[i][j], H1field[i][j], H2field[i][j], H12field[i][j], Qfield[i][j]); 
  fclose(h);
  if(PrintFlag) printf("done.\n");
  return;
}

//////////////////////////////////////////////////////////////////

void HTable::read(char* name )
{
  FILE* h;
  int i,j;
  int fscanfresult __attribute__ ((unused));
  char x1[STRSIZE], x2[STRSIZE],x3[STRSIZE],x4[STRSIZE],x5[STRSIZE] ;
  if(PrintFlag) printf("Read H table from file %s\n", name);
  if(( h = fopen(name,"r"))==NULL) {
    printf("\nLIB-ERROR in HTable::read ---> %s not found !!!\n",name);
    exit(0);
  }
  fscanfresult = fscanf(h,"%s %s",x1,x2 );
  NU = atoi(x1);
  NT = atoi(x2);
  if(PrintFlag) printf("%d   %d\n",NU,NT );
  ufield = dvector(1,NU);
  Tfield = dvector(1,NT);
  Hfield   = dmatrix(1,NU,1,NT); 
  H1field  = dmatrix(1,NU,1,NT); 
  H2field  = dmatrix(1,NU,1,NT); 
  H12field = dmatrix(1,NU,1,NT);
  Qfield   = dmatrix(1,NU,1,NT);
  
  for(i=1;i<=NU;i++) { fscanfresult = fscanf(h,"%s",x1); ufield[i] = atof(x1); }
  for(j=1;j<=NT;j++) { fscanfresult = fscanf(h,"%s",x1); Tfield[j] = atof(x1); }
  for(i=1;i<=NU;i++) 
    for(j=1;j<=NT;j++) {
      fscanfresult = fscanf(h,"%s  %s  %s  %s  %s",x1,x2,x3,x4,x5 );
      Hfield[i][j]   = atof(x1);
      H1field[i][j]  = atof(x2);
      H2field[i][j]  = atof(x3);
      H12field[i][j] = atof(x4);
      Qfield[i][j]   = atof(x5);
    }
  if(PrintFlag) printf("done.\n");
  return;
}

//////////////////////////////////////////////////////////////////

void HTable::kill(void)
{
  if(PrintFlag) printf("\n Free memory from H table...");
  free_dvector(ufield,1,NU);
  free_dvector(Tfield,1,NT);
  delete_dmatrix(Hfield,1,NU,1,NT); 
  delete_dmatrix(H1field,1,NU,1,NT);
  delete_dmatrix(H2field,1,NU,1,NT); 
  delete_dmatrix(H12field,1,NU,1,NT);
  delete_dmatrix(Qfield,1,NU,1,NT); 
  if(PrintFlag) printf("done.\n");
  return;
}

//////////////////////////////////////////////////////////////////
// eof.