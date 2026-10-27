//////////////////////////////////////////////////////////////////
// service routines for table interpolations 
// used by the SHOWEOS table visualization tool
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#include "SE-02_INTERPOLTOOLS.H"

//////////////////////////////////////////////////////////////////

double fi( Qtable* qtab, Units* units, int eostype, 
           double rho, double t, double ro , double eo, double po )
{
  // make this function zero in Hugoniot
  double e, p, res;
 
  p = GetQuantity( 4, qtab, rho, t, 0, eostype, units );
  e = GetQuantity( 5, qtab, rho, t, 0, eostype, units );   
  res = ro*( p+po) / ( (p+po) - 2.0*ro*(e-eo) ) - rho;
  
  return res;
}

//////////////////////////////////////////////////////////////////

double get_PQ_LI( double* rho, double* T, double r, double t, double** PQ, 
		  int NR, int NT )
{
  double pq;
  int ig=0,jg =0;
  shift_box( &ig, &jg, rho, T , r, t, NR,NT );
  interpol( rho, T, PQ, r, t, &pq, ig, jg );
  return pq;
}

//////////////////////////////////////////////////////////////////

void polint(double* xa,double* ya,int n,double x,double* y,double* dy)

{
	int i,m,ns=1;
	double den,dif,dift,ho,hp,w;
	double *c,*d;

	dif=fabs(x-xa[1]);
	c=dvector(1,n);
	d=dvector(1,n);
	for (i=1;i<=n;i++) {
		if ( (dift=fabs(x-xa[i])) < dif) {
			ns=i;
			dif=dift;
		}
		c[i]=ya[i];
		d[i]=ya[i];
	}
	*y=ya[ns--];
	for (m=1;m<n;m++) {
		for (i=1;i<=n-m;i++) {
			ho=xa[i]-x;
			hp=xa[i+m]-x;
			w=c[i+1]-d[i];
			if ( (den=ho-hp) == 0.0) printf("\nSE-ERROR in polint !!!\n");
			den=w/den;
			d[i]=hp*den;
			c[i]=ho*den;
		}
		*y += (*dy=(2*ns < (n-m) ? c[ns+1] : d[ns--]));
	}
	free_dvector(d,1,n);
	free_dvector(c,1,n);
	return;
}

//////////////////////////////////////////////////////////////////

void polin2(double* x1a,double* x2a,double **ya,int m,int n,double x1,double x2,double* y,double* dy)
{
	int j;
	double *ymtmp;

	ymtmp=dvector(1,m);
	for (j=1;j<=m;j++) {
		polint(x2a,ya[j],n,x2,&ymtmp[j],dy);
	}
	polint(x1a,ymtmp,m,x1,y,dy);
	free_dvector(ymtmp,1,m);
	return;
}

//////////////////////////////////////////////////////////////////

void interpol(double* rho_, double* T_,double** PQ, double rho, double t, double* pq,int i0, int j0 )
{
  int i,j;
  double *x1a,
    *x2a,
    **ya,
    *y1a;
  double dy;             // error estimate 

  x1a = dvector(1,2);

  if(t>0.0) {
    ya = dmatrix(1,2,1,2);
    x2a = dvector(1,2);
    for( i=1; i<= 2; i++) { 
      x1a[i] = rho_[i0+i-1];
      x2a[i] = T_[j0+i-1];
      for(j=1;j<=2;j++) ya[i][j] = PQ[i0-1+i][j0-1+j];  // erstelle untermatrix f. polint
    }
    polin2( x1a, x2a, ya, 2, 2, 
	    rho, t, pq, &dy ); 

    delete_dmatrix( ya, 1,2,1,2 );
    free_dvector(x2a,1,2);
  } 
  else {
    y1a = dvector(1,2);
    for( i=1; i<= 2; i++) { 
      x1a[i] = rho_[i0+i-1]; 
      y1a[i] = PQ[i0-1+i][1]; 
    }
    polint( x1a, y1a, 2, rho, pq, &dy );
    free_dvector(y1a,1,2);
  }
  free_dvector(x1a,1,2);
  return;
}

//////////////////////////////////////////////////////////////////
// eof.