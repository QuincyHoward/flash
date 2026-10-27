//////////////////////////////////////////////////////////////////
// routines to get thermodynamic functions without Maxwell construction  
// used by the FEOS library
// last change: 2016-07-29
//////////////////////////////////////////////////////////////////

#include "LIB-05_EOS_SERVICES.H"

//////////////////////////////////////////////////////////////////

void GetElectronEOSQuantities( Ionpart* ionp, QIPscheme** qipp, int corrections, double Rho, double T,
       double* p, double* e, double* s, double* f, double* q, double* qtot,
       double* pTF, double* eTF, double* sTF, double* fTF )
{
  // compute all thermodynamical quantities for electrons; 

  double pb, eb, ps, es, eec, pec, fec, sec, qtotec, *qec;
  qec = new double[(*ionp).Nelements];

  // Get pure TF contribution:
  mixture_getTFquantities(qipp, ionp, Rho, T, pTF, eTF, sTF, fTF, q, qtot); 

  // Subtract offset to make energy zero at reference conditions:
  *eTF -= (*ionp).Ee_Offset;
  *fTF -= (*ionp).Ee_Offset;
  
  // Calculate the electron contribution with corrections:
  if(corrections) {
    *p = *pTF; *e = *eTF; *s = *sTF; *f = *fTF;
    // calculation with Soft Sphere Function 
    if((*ionp).SoftSphereFlag && Rho<(*ionp).rhosolid) {
      mixture_getTFquantities(qipp, ionp, Rho, 0.0, &pec, &eec, &sec, &fec, qec, &qtotec);
      (*ionp).getSoftSphereQuantities( Rho, &ps, &es );
      *p -= pec; *p += ps;
      *e -= eec; *e += es;
      *f -= eec; *f += es;                          
    }
    // or with Bonding Correction
    else {
      (*ionp).get_bonding_contrib( Rho, &pb, &eb );
      *p += pb;
      *e += eb;
      *f += eb;            
    }    
  }
  else *p = *e = *s = *f = NOTCALCULATED_QUANTITY;   

  delete qec;

  return;
}

//////////////////////////////////////////////////////////////////

void GetIonEOSQuantities( Ionpart* ionp, QIPscheme** qipp, double Rho, double T,
		 	 double* p, double* e, double* s, double* f )
{
  // compute all thermodynamical quantities for ions; 

  (*ionp).getIonicQuantities(  Rho, T, p, e, f, s );

  // Subtract offset to make energy zero at reference conditions:
  *e -= (*ionp).Ei_Offset;
  *f -= (*ionp).Ei_Offset;

  return;
}

//////////////////////////////////////////////////////////////////

void GetAllEOSQuantities( Ionpart* ionp, QIPscheme** qipp, int task, double Rho, double T,
		 	 double* p, double* e, double* s, double* f, double* q, double* qtot,
       double* pe, double* ee, double* se, double* fe,
       double* pi, double* ei, double* si, double* fi,
       double* pTF, double* eTF, double* sTF, double* fTF )
{
  // compute thermodynamical quantities by choice;
   
  int i;
   
  if(task != 1) GetElectronEOSQuantities( ionp, qipp, abs(3-task), Rho, T, 
                   pe, ee, se, fe, q, qtot, pTF, eTF, sTF, fTF );
  else {
    *pe = *ee = *se = *fe = *qtot = *pTF = *eTF = *sTF = *fTF = NOTCALCULATED_QUANTITY;
    for(i=0; i<(*ionp).Nelements; i++) { q[i] = NOTCALCULATED_QUANTITY; }    
  }                          

  if(task != 2 && task != 3) GetIonEOSQuantities( ionp, qipp, Rho, T, pi, ei, si, fi );
  else *pi = *ei = *si = *fi = NOTCALCULATED_QUANTITY;
 
  if(task != 1 && task != 2 && task !=3) {
    *p = *pi + *pe;
    *e = *ei + *ee;
    *f = *fi + *fe;
    *s = *si + *se;
  }
  else *p = *e = *f = *s = NOTCALCULATED_QUANTITY;

  return;
}

//////////////////////////////////////////////////////////////////

void GetTotalEOSQuantities( Ionpart* ionp, QIPscheme** qipp, double Rho, double T,
		 	 double* p, double* e, double* s, double* f, double* q, double* qtot )
{
  // compute thermodynamical quantities of total EOS;
   
  double p1, p2, p3, e1, e2, e3, s1, s2, s3, f1, f2, f3;

  GetAllEOSQuantities( ionp, qipp, 0, Rho, T, p, e, s, f, q, qtot,
       &p1, &e1, &s1, &f1, &p2, &e2, &s2, &f2, &p3, &e3, &s3, &f3 );
  return;
}

//////////////////////////////////////////////////////////////////

void getPmax_Pmin( Ionpart* ionp, QIPscheme** qipp, double t, 
         double *Pmax, double *Rmax, double *Pmin, double *Rmin, int printflag )
{
  // calculates maximum and minimum pressure of Van-der-Waals loop on isotherm T = t

  double p,r,e,f,s,*q,qtot,fac;
  q = new double[(*ionp).Nelements];

  fac = 1.0 + DELTA_R_GETPMAXPMIN;
  
  // search maximum pressure, start at some reasonable density
  if(RHO_ZERO < START_R_GETPMAX) r = START_R_GETPMAX;
  else r = RHO_ZERO;
  GetTotalEOSQuantities( ionp, qipp, r,t,&p,&e,&s,&f,q,&qtot );
  do {
    *Rmax = r;
    *Pmax = p;    
    r *= fac;
    GetTotalEOSQuantities( ionp, qipp, r,t,&p,&e,&s,&f,q,&qtot );
  } while( p >= *Pmax );  
  if(printflag && (*ionp).PrintFlag) printf( "   Rhomax = %e g/cm^3, Pmax = %+e dyne/cm^2\n", *Rmax, *Pmax );

  // search minimum pressure, start at some reasonable density
  r = START_R_GETPMIN;
  GetTotalEOSQuantities( ionp, qipp, r,t,&p,&e,&s,&f,q,&qtot );  
  do {
    *Rmin = r;
    *Pmin = p;
    r /= fac;
    GetTotalEOSQuantities( ionp, qipp, r,t, &p, &e,&s,&f,q,&qtot );
  } while( p <= *Pmin && r >= RHO_ZERO );
  if(printflag && (*ionp).PrintFlag) printf( "   Rhomin = %e g/cm^3, Pmin = %+e dyne/cm^2\n", *Rmin, *Pmin );

  delete q;

  return;
}

//////////////////////////////////////////////////////////////////

int contains_loop( Ionpart* ionp, QIPscheme** qipp, double t, double t_containing )         
{  
  // tests for Van-der-Waals loop on isotherm T = t
  // factor CONTAINS_LOOP_DELTA_R controls precision
  // factor NUM_NOISE means to be careful about numerical noise in low-temperature isotherms.

  double MaxP, MaxR, MinP, MinR;
  double r,p,e,s,f,*q,qtot;
  q = new double[(*ionp).Nelements];

  if( t<t_containing ) t_containing = T_ZERO;  
  
  getPmax_Pmin( ionp, qipp, t_containing, &MaxP, &MaxR, &MinP, &MinR, 0 );
  r = MaxR/(1.0+2*CONTAINS_LOOP_PREC_R);
  GetTotalEOSQuantities( ionp, qipp, r,t, &MaxP, &e,&s,&f,q,&qtot );
  while(r<=MinR*(1.0+2*CONTAINS_LOOP_PREC_R)) {
    r *= (1.0+CONTAINS_LOOP_PREC_R);
    GetTotalEOSQuantities( ionp, qipp, r,t, &p, &e,&s,&f,q,&qtot );
    if( p > MaxP ) MaxP = p;
    else if (p < CONTAINS_LOOP_NUM_NOISE*MaxP) return 1; // loop found!
  }

  delete q;

  return 0;
}

//////////////////////////////////////////////////////////////////

double getRofP( Ionpart* ionp, QIPscheme** qipp, double t, double p, double x1, double x2, bool* failure, int printflag )
{ 
  // returns density as function of T and pressure
  // x1 and x2: appropriate guess for the bracketing densities on isotherm T = t
  
  int j;
  double dx,f,fmid,xmid,rtb;
  double xtemp,prec,ye,ys,yf,*yq,yqtot;
  yq = new double[(*ionp).Nelements];

  if(x1<RHO_ZERO) x1=RHO_ZERO;
  if(x2<RHO_ZERO) x2=RHO_ZERO;

  // get better bracketing densities
  if(x1>x2) { xtemp = x2; x2 = x1; x1 = xtemp; }
  GetTotalEOSQuantities( ionp, qipp, x1,t, &f,&ye,&ys,&yf,yq,&yqtot );  
  GetTotalEOSQuantities( ionp, qipp, x2,t, &fmid,&ye,&ys,&yf,yq,&yqtot );
  if(f<=p) {
    for (j=1;j<=500;j++) {
      xtemp=x1*10.0;
      if(xtemp>=x2) break;
      GetTotalEOSQuantities( ionp, qipp, xtemp,t, &f,&ye,&ys,&yf,yq,&yqtot ); 
      if(f>=p) { x2=xtemp; break; }
      x1=xtemp;
    }
  }
  else {
    for (j=1;j<=500;j++) {
      xtemp=x1*10.0;
      if(xtemp>=x2) break;
      GetTotalEOSQuantities( ionp, qipp, xtemp,t, &f,&ye,&ys,&yf,yq,&yqtot ); 
      if(f<=p) { x2=xtemp; break; }
      x1=xtemp;
    }
  }   

  // find density
  GetTotalEOSQuantities( ionp, qipp, x1,t, &f,&ye,&ys,&yf,yq,&yqtot );  
  GetTotalEOSQuantities( ionp, qipp, x2,t, &fmid,&ye,&ys,&yf,yq,&yqtot );
  f -= p; fmid -= p;
  if (f*fmid >= 0.0) { 
    if(printflag) printf( "   ERROR: getRofP ---> Root must be bracketed for bisection !!!\n" );
    *failure = true;
    delete yq;
    return 0.0;   
  }
  rtb = f < 0.0 ? (dx=x2-x1,x1) : (dx=x1-x2,x2);
  prec = fabs(dx) * eps_getR;
  for (j=1;j<=100;j++) {
    GetTotalEOSQuantities( ionp, qipp,  xmid=rtb+(dx *= 0.5),t, &fmid,&ye,&ys,&yf,yq,&yqtot );
    fmid -= p;
    if (fmid <= 0.0) rtb=xmid;
    if (fabs(dx) < prec || fmid == 0.0) {*failure = false; delete yq; return rtb;}
  }
  if(printflag) printf("   ERROR: getRofP ---> Too many bisections !!!\n");
  *failure = true;  
  delete yq;
  return 0.0;   
}  

//////////////////////////////////////////////////////////////////
// eof.