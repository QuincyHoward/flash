//////////////////////////////////////////////////////////////////
// routines for calculation of the Maxwell construction  
// used by the FEOS library
// last change: 2016-07-29
//////////////////////////////////////////////////////////////////
// Class CriticalData is called in main program
// if (MaxwellFlag): 
//    compute critical point in CritPoint
//    compute vaporisation curve in vaporisation_curve
//    store this curve and pressure values belonging to that
// else:
//    set Critical Data to zero
//////////////////////////////////////////////////////////////////

#include "LIB-06_MAXWELL.H"

//////////////////////////////////////////////////////////////////

CriticalData::CriticalData( Ionpart* ip, QIPscheme** qip, double* MaxwellTtab, int MaxwellNT )
{
  int i;

  if(MaxwellNT<0) {
	  printf("\nLIB-ERROR in CriticalData::CriticalData ---> Number of isotherms for Maxwell construction < 0 !!!\n");
	  exit(0);
	}

  Tindexend    = MaxwellNT - 1;
  MAXVAP       = MaxwellNT; 
  ionpart_cd   = ip;
  qipscheme_cd = qip;
  FoundGoodT   = false;
  failure      = false;
  PrintFlag    = (*ip).PrintFlag;

  Ttable = dvector(0,Tindexend);
  for(i=0;i<=Tindexend;i++) Ttable[i] = MaxwellTtab[i];  

  data.Rhol = dvector(0,MAXVAP);
  data.Rhov = dvector(0,MAXVAP);
  data.Pl = dvector(0,MAXVAP);
  data.Pv = dvector(0,MAXVAP);
  data.Peq = dvector(0,MAXVAP);
  data.Tiso = dvector(0,MAXVAP);
  data.Rhomax = dvector(0,MAXVAP);
  data.Rhomin = dvector(0,MAXVAP);
  data.Pmin = dvector(0,MAXVAP);
  data.Pmax = dvector(0,MAXVAP);
  data.Gl = dvector(0,MAXVAP);
  data.Gv = dvector(0,MAXVAP);
  data.Hl = dvector(0,MAXVAP);
  data.Hv = dvector(0,MAXVAP);
  data.Zl = dvector(0,MAXVAP);
  data.Zv = dvector(0,MAXVAP);

  for(i=0; i<=MAXVAP; i++) 
    data.Rhol[i] = data.Rhov[i] = data.Pl[i] = data.Pv[i] = data.Peq[i] = data.Tiso[i] = data.Rhomax[i] = data.Rhomin[i] =
    data.Pmin[i] = data.Pmax[i] = data.Gl[i] = data.Gv[i] = data.Hl[i] = data.Hv[i] = data.Zl[i] = data.Zv[i] = 0.0; 

  if ((*ip).MaxwellFlag) {
    if(MaxwellNT<1) {
	    printf("\nLIB-ERROR in CriticalData::CriticalData ---> Number of isotherms for Maxwell construction < 1 !!!\n");
	    exit(0);
	  }
    CritPoint();
    vaporisation_curve();
    BoilingTemperature();
  } 
  else {
    data.Niso = 0;                      // reset values to zero
    data.Rhoc = data.Pc = data.Tc = data.Hc = data.Zc = data.Sc = data.Tb = data.Trel = 0.0;
  }
}

//////////////////////////////////////////////////////////////////

CriticalData::~CriticalData()
{
  // free memory
  free_dvector( Ttable,0,Tindexend );
  
  free_dvector( data.Rhol,0,MAXVAP ); 
  free_dvector( data.Rhov,0,MAXVAP );
  free_dvector( data.Pl,0,MAXVAP ); 
  free_dvector( data.Pv,0,MAXVAP );
  free_dvector( data.Peq,0,MAXVAP );  
  free_dvector( data.Tiso,0,MAXVAP );
  free_dvector( data.Rhomin,0,MAXVAP ); 
  free_dvector( data.Rhomax,0,MAXVAP ); 
  free_dvector( data.Pmin,0,MAXVAP ); 
  free_dvector( data.Pmax,0,MAXVAP ); 
  free_dvector( data.Gl,0,MAXVAP ); 
  free_dvector( data.Gv,0,MAXVAP );
  free_dvector( data.Hl,0,MAXVAP ); 
  free_dvector( data.Hv,0,MAXVAP );
  free_dvector( data.Zl,0,MAXVAP ); 
  free_dvector( data.Zv,0,MAXVAP ); 
}

//////////////////////////////////////////////////////////////////

double CriticalData::derivP1( double r, double t )
{
  // first derivative of pressure w.r.t.  density
  
  double dr,p1,p2,p3,dp,e,s,f,*q,qtot;
  q = new double[(*ionpart_cd).Nelements];
         
  if (r<ZERO) { printf("\nLIB-ERROR in CriticalData::derivP1 ---> r <= 0 !!!\n" );exit(0); }
  dr = r * 0.01;
  
  GetTotalEOSQuantities( ionpart_cd, qipscheme_cd, r-dr,t, &p1, &e,&s,&f,q,&qtot );
  GetTotalEOSQuantities( ionpart_cd, qipscheme_cd, r,t, &p2, &e,&s,&f,q,&qtot );
  GetTotalEOSQuantities( ionpart_cd, qipscheme_cd, r+dr,t, &p3, &e,&s,&f,q,&qtot );
  dp = (p3-p1)/2.0;
  // d2p = (p3-2.0*p2+p1)/(dr*dr);

  delete q;
  
  return dp; 
}
 
//////////////////////////////////////////////////////////////////

void CriticalData::CritPoint()
{
  // find the critical point
  
  double p,r=0.0,t=0.0,
         e,s,f,*q,qtot,
         Tmin,Tmax,
         dpmin,Rmin,Rmax,Pma,Pmi;
  double Amean = (*ionpart_cd).Amean;
  q = new double[(*ionpart_cd).Nelements];

  double dp;
  if(PrintFlag) printf( "\n Find critical point:\n" );
  Tmin = T_ZERO;
  Tmax = Ttable[Tindexend];
  if(contains_loop(ionpart_cd, qipscheme_cd, Tmax, T_ZERO)) {
    printf("\nLIB-ERROR in CriticalData::CritPoint ---> Highest input temperature must be above the critical point !!!\n");
    exit(0);
  } 
  while( (Tmax-Tmin)/Tmax > epsT ) {  //    1) which isotherms contain loops ?
    t = 0.5*( Tmin + Tmax );
    if(contains_loop(ionpart_cd, qipscheme_cd, t, Tmin) ) Tmin = t;
    else Tmax = t;
  }
  getPmax_Pmin( ionpart_cd, qipscheme_cd, t/2.0, &Pma,&r,&Pmi, &Rmax, 0 ); 
  dpmin = derivP1( r,t );
  Rmin = r;
  while(r <= Rmax) {
    r = r * (1.0+100.0*epsR);
    dp = derivP1( r,t );
    if(dp < dpmin) {
      dpmin = dp;
      Rmin = r;
    }
  }
  r = Rmin / (1.0+100.0*epsR);
  dpmin = derivP1( r,t );
  Rmax = Rmin;
  while(r <= Rmax) {
    r = r * (1.0+epsR);
    dp = derivP1( r,t );
    if(dp < dpmin) {
      dpmin = dp;
      Rmin = r;
    }
  }
  r = Rmin;

  GetTotalEOSQuantities( ionpart_cd, qipscheme_cd, r,t, &p, &e,&s,&f,q,&qtot );
  data.Rhoc = r;
  data.Trel = data.Tc = t;
  data.Pc = p;
  data.Hc = e + ( p / r );
  data.Sc = s;
  data.Zc = p*Amean/(r*t*GAS_CONSTANT);
  if(PrintFlag) printf( "  Rhoc = %e g/cm^3\n  Tc = %e eV\n  Pc = %e dyne/cm^2\n", data.Rhoc, data.Tc, data.Pc ); 
  
  if(r<RHO_ZERO) {
    printf("\nLIB-ERROR in CriticalData::CritPoint ---> Critical density below library density limit !!!\n");
    exit(0);
  } 
  if(t<T_ZERO) {
    printf("\nLIB-ERROR in CriticalData::CritPoint ---> Critical temperature below library temperature limit !!!\n");
    exit(0);
  } 
  
  if(PrintFlag) printf(" Done.\n"); 

  delete q;
  
  return;
}

//////////////////////////////////////////////////////////////////

double CriticalData::gibbsfreedifference( double t, double p, 
				  double *rl, double *rv,
				  double Rmin, double Rmax,
				  double Pmin, double Pmax, double P_smallR)
{ 
  // return the difference of Gibbs free energy between vapor and liquid side for given p
  
  double Rliq, Rvap, Gliq, Gvap, dG;
  double yp,ye,ys,yf,*yq,yqtot;
  yq = new double[(*ionpart_cd).Nelements];

  if(p==Pmax) Rvap = Rmax;
  else if(p==P_smallR) Rvap = RHO_ZERO;
  else {
    Rvap = getRofP( ionpart_cd, qipscheme_cd, t, p, RHO_ZERO, Rmax, &failure, PrintFlag );
    if(failure) { delete yq; return 0.0; }
  }
  if(p==Pmin) Rliq = Rmin;
  else {
    Rliq = getRofP( ionpart_cd, qipscheme_cd, t, p, Rmin, (*ionpart_cd).rhosolid*1.0e2, &failure, PrintFlag );
    if(failure) { delete yq; return 0.0; }
  }
  GetTotalEOSQuantities( ionpart_cd, qipscheme_cd, Rliq, t, &yp,&ye,&ys,&yf,yq,&yqtot );
  Gliq = ( yp / Rliq ) + yf;
  GetTotalEOSQuantities( ionpart_cd, qipscheme_cd, Rvap, t, &yp,&ye,&ys,&yf,yq,&yqtot );
  Gvap = ( yp / Rvap ) + yf;
  dG = Gvap - Gliq;
  *rl = Rliq;
  *rv = Rvap;
  delete yq;  
  return dG;
}

//////////////////////////////////////////////////////////////////

double CriticalData::bisection( double t, double *r1,double *r2, 
				double Pmax, double Pmin, 
				double Rmin, double Rmax )
{ 
  double x1,x2;
  x1 = Pmax;
  x2 = Pmin;
  int j;
  double dx,f,fmid,xmid,rtb;
  double Gliq,Rliq,G_smallR,P_smallR;
  double xtemp,prec,yp,ye,ys,yf,*yq,yqtot;
  yq = new double[(*ionpart_cd).Nelements];

  // Check existence of densities with equal Gibbs free energy and pressure
  GetTotalEOSQuantities( ionpart_cd, qipscheme_cd, RHO_ZERO, t, &P_smallR,&ye,&ys,&yf,yq,&yqtot );
  if(P_smallR>Pmin) {
    G_smallR = ( P_smallR / RHO_ZERO ) + yf;
    Rliq = getRofP( ionpart_cd, qipscheme_cd, t, P_smallR, Rmin, (*ionpart_cd).rhosolid*1.0e2, &failure, PrintFlag );
    if(failure) { delete yq; return 0.0; }
    GetTotalEOSQuantities( ionpart_cd, qipscheme_cd, Rliq, t, &yp,&ye,&ys,&yf,yq,&yqtot );
    Gliq = ( yp / Rliq ) + yf;
    if(Gliq<G_smallR) { 
      if(PrintFlag) printf("   WARNING: No densities > %e g/cm^3 with equal Gibbs free energy!\n", RHO_ZERO );
      if(P_smallR<=0.0) return 0.0;
      if(PrintFlag) printf("            -> Peq set to P(%e g/cm^3,T)!\n", RHO_ZERO );
      *r1 = Rliq;
      *r2 = RHO_ZERO;
	  delete yq;      
      return P_smallR;
    }
    x2 = P_smallR;
  }

  // get better bracketing pressures
  f    = gibbsfreedifference( t, x1, r1, r2, Rmin, Rmax, Pmin, Pmax, P_smallR );
  if(failure) { delete yq; return 0.0; }
  fmid = gibbsfreedifference( t, x2, r1, r2, Rmin, Rmax, Pmin, Pmax, P_smallR );
  if(failure) { delete yq; return 0.0; }
  for (j=1;j<=500;j++) {
    xtemp=x1/10.0;
    if(xtemp<=x2) break;
    f = gibbsfreedifference( t, xtemp, r1, r2, Rmin, Rmax, Pmin, Pmax, P_smallR );
    if(failure) { delete yq; return 0.0; } 
    if(f<=0.0) { x2=xtemp; break; }
    x1=xtemp;
  }
  
  // find densities and pressure
  f    = gibbsfreedifference( t, x1, r1, r2, Rmin, Rmax, Pmin, Pmax, P_smallR );
  if(failure) { delete yq; return 0.0; }
  fmid = gibbsfreedifference( t, x2, r1, r2, Rmin, Rmax, Pmin, Pmax, P_smallR );
  if(failure) { delete yq; return 0.0; }
  if (f*fmid >= 0.0) {
    Rliq = getRofP( ionpart_cd, qipscheme_cd, t, P_smallR, Rmin, (*ionpart_cd).rhosolid*1.0e2, &failure, PrintFlag );
    if(failure) { delete yq; return 0.0; }
    if(PrintFlag) printf( "   WARNING: Failed to find equal Gibbs free energies!\n" );
    if(P_smallR<=0.0) return 0.0;
    if(PrintFlag) printf( "            -> Peq set to P(%e g/cm^3,T)!\n", RHO_ZERO); 
    *r1 = Rliq;
    *r2 = RHO_ZERO;
	delete yq;    
    return P_smallR;
  }
  rtb = f < 0.0 ? (dx=x2-x1,x1) : (dx=x1-x2,x2);
  prec = fabs(dx) * eps_bisect;
  for (j=1;j<=100;j++) {
    fmid = gibbsfreedifference( t, xmid=rtb+(dx *= 0.5) , r1, r2 , Rmin, Rmax, Pmin, Pmax, P_smallR );
    if(failure) { delete yq; return 0.0; }
    if (fmid <= 0.0) rtb=xmid;
    if (fabs(dx) < prec || fmid == 0.0) {
      if(!FoundGoodT) { data.Trel = t; FoundGoodT = true; }
      delete yq;
      return rtb;
    }
  }
  if(PrintFlag) printf("   ERROR: CriticalData::bisection ---> Too many bisections!\n");
  delete yq;
  failure = true;
  return 0.0;
}

//////////////////////////////////////////////////////////////////

void CriticalData::vaporisation_curve() 
{ 
  // index i of vaporisation curve goes like 0 .. (Niso - 1) 
  
  double t, Pma, Pmi, Rma, Rmi, R1, R2, tprev;
  int j;
  double p,e,s,f,*q,qtot;
  double Amean = (*ionpart_cd).Amean;
  bool LowT = false;
  q = new double[(*ionpart_cd).Nelements];

  j = data.Niso = 0;
  tprev = -1.0;
  if(PrintFlag) printf( "\n Calculate two-phase boundary (binodal) by finding equal Gibbs free energies:\n" );
  
  if(Ttable[0]>T_ZERO) {
    if(PrintFlag) printf("  Lower temperature limit T = %.2e eV is added to the Maxwell table!\n", T_ZERO);
    LowT = true;  
  }

  // perform Maxwell construction isotherm by isotherm for T < Tc  
  while( (t = Ttable[j]) < data.Tc ) {
    // initial temperature check and printout
    if(j>Tindexend) {
	    printf("\nLIB-ERROR in CriticalData::vaporisation_curve ---> Temperature table exceeded !!!\n");
	    exit(0);    
    }
    if(LowT) {
      t = T_ZERO;
      j = j - 1;
    }
    if(PrintFlag) printf( "  T = %e eV:\n",t); 
    if(t<T_ZERO) {
      if(t*(1.0+1.0e-7)<T_ZERO) { 
        if(PrintFlag) printf("   WARNING: T below library temperature limit!\n");
        if(PrintFlag) printf("            -> Calculation will be done for T = %.2e eV!\n", T_ZERO);
      }
      t = T_ZERO;
    }       
    if(j>=0) {
      if(Ttable[j]<=tprev) {
        if(PrintFlag) printf("   WARNING: T smaller or equal to the last calculated temperature!\n");
        if(PrintFlag) printf("            -> Temperature will be skipped!\n");
        j = j + 1;
        continue;
      }
    }
    // get min and max pressure of isotherm, as starting values of bisectioning (T>0)   
    getPmax_Pmin( ionpart_cd, qipscheme_cd, t, &Pma,&Rma,&Pmi, &Rmi, 1 ); 
    data.Rhomin[data.Niso] = Rmi; data.Rhomax[data.Niso] = Rma; data.Pmin[data.Niso] = Pmi; data.Pmax[data.Niso] = Pma;
    // get equilibrium pressure and densities on vaporisation curve
    if(t!=0.0) {
      data.Peq[data.Niso] = bisection( t, &R1, &R2, Pma, Pmi, Rmi, Rma );
      if(failure) {
        if(PrintFlag) printf("          -> Temperature will be skipped!\n");
        failure=false;
        LowT = false;
        j = j + 1;
        continue;
      }
    }
    else {
	    if(Pmi<=0.0) {
        R1 = getRofP( ionpart_cd, qipscheme_cd, t, 0.0, Rmi*0.99, (*ionpart_cd).rhosolid*10, &failure, PrintFlag );
        if(failure) {
          if(PrintFlag) printf("          -> Temperature will be skipped!\n");
          if(FoundGoodT && data.Trel == t) {FoundGoodT = false; data.Trel = 0.0;}
          failure=false;
          LowT = false;
          j = j + 1;
          continue;        
        }
      }
	    else {
	      if(PrintFlag) printf("   ERROR: CriticalData::vaporisation_curve ---> No pressure P = 0 found !!!\n");
        if(PrintFlag) printf("          -> Temperature will be skipped!\n");
        if(FoundGoodT && data.Trel == t) {FoundGoodT = false; data.Trel = 0.0;}
        LowT = false;
        j = j + 1;
        continue;  
	    }
	    R2 = RHO_ZERO;
	    data.Peq[data.Niso] = 0.0;
      if(PrintFlag) printf("   -> Peq set to zero for Rho < %e g/cm^3!\n",R1);
    }
    if(t!=0.0 && data.Peq[data.Niso]<=0.0) {
      if(PrintFlag) printf("   ERROR: CriticalData::vaporisation_curve ---> Non-positive Peq for T = %e eV !!!\n", t);
      if(PrintFlag) printf("          -> Temperature will be skipped!\n");
      if(FoundGoodT && data.Trel == t) {FoundGoodT = false; data.Trel = 0.0;}
      LowT = false;
      j = j + 1;
      continue; 
    }
    if(PrintFlag) printf( "   Peq[%d] = %e dyne/cm^2\n" , data.Niso+1, data.Peq[data.Niso] );
    // calculate and store all quantities on vaporisation curve
    data.Tiso[data.Niso] = tprev = t;          
	  data.Rhol[data.Niso] = R1;
	  data.Rhov[data.Niso] = R2;
    GetTotalEOSQuantities( ionpart_cd, qipscheme_cd, R1, t, &p,&e,&s,&f,q,&qtot );
    data.Pl[data.Niso] = p;
    data.Gl[data.Niso] = ( p / R1 ) + f;
    data.Hl[data.Niso] = ( p / R1 ) + e;
    data.Zl[data.Niso] = p * Amean / (R1 * t * GAS_CONSTANT);
    GetTotalEOSQuantities( ionpart_cd, qipscheme_cd, R2, t, &p,&e,&s,&f,q,&qtot );
    data.Pv[data.Niso] = p;
    data.Gv[data.Niso] = ( p / R2 ) + f;
    data.Hv[data.Niso] = ( p / R2 ) + e;
    data.Zv[data.Niso] = p * Amean / (R2 * t * GAS_CONSTANT);
		if(PrintFlag) printf( "   Rholiq = %e g/cm^3, Rhovap = %e g/cm^3\n", data.Rhol[data.Niso], data.Rhov[data.Niso] );
    if(PrintFlag) printf( "   P(Rhovap,T) = %+e dyne/cm^2, G(Rhovap,T) = %+e erg/g\n", data.Pv[data.Niso], data.Gv[data.Niso] );
    if(PrintFlag) printf( "   P(Rholiq,T) = %+e dyne/cm^2, G(Rholiq,T) = %+e erg/g\n", data.Pl[data.Niso], data.Gl[data.Niso] );
    //   
    j = j + 1;
    data.Niso = data.Niso + 1;
    LowT = false;
  }

  if(FoundGoodT && PrintFlag) printf("  Maxwell construction data reliable for T >= %e eV!\n", data.Trel);
  else if(PrintFlag) printf("  WARNING: No reliable data calculated below the critical point!\n");
  if(PrintFlag) printf(" Done.\n");
  delete q;
  return;
}

//////////////////////////////////////////////////////////////////

void CriticalData::BoilingTemperature()
{ 
  // Find boiling temperature (saturation pressure = 1bar)
    
  int c;
  if(PrintFlag) printf( "\n Find boiling temperature (saturation pressure: 1.0e06 dyne/cm^2):\n" );

  if((data.Peq[0]*cgs2Bar)>1.0 || (data.Pc*cgs2Bar)<1.0 ) {
    if(PrintFlag) printf( "  ERROR: CriticalData::BoilingTemperature ---> Boiling temperature out of Maxwell data range !!!\n");
    data.Tb = 0.0;
    return;  
  }

  // Find bracketing values for boiling temperature
  c = 0;
  while( 1.0 > (data.Peq[c]*cgs2Bar) && c < data.Niso-1) c++;

  // Find boiling temperature by linear interpolation in Arrhenius coordinates
  if(c==data.Niso-1) 
    data.Tb = 1.0/Linear_Interpol( log10(data.Peq[c]), log10(data.Pc),
			                             1.0/data.Tiso[c], 1.0/data.Tc, 6.0 );
  else 
    data.Tb = 1.0/Linear_Interpol( log10(data.Peq[c]), log10(data.Peq[c+1]),
			                             1.0/data.Tiso[c], 1.0/data.Tiso[c+1], 6.0 );
			                             
  if(PrintFlag) printf("  Interpolation in Arrhenius coordinates: Tb = %e eV\n Done.\n", data.Tb);    
  return;
}  

//////////////////////////////////////////////////////////////////

void GetAllMaxwellEOSQuantities( Ionpart* ionp, QIPscheme** qipp, CriticalData* Critical,  
       int task, int Maxwell, double Rho, double T, int* BelowBinodal,
		 	 double* p, double* e, double* s, double* f, double* q, double* qtot,
       double* pe, double* ee, double* se, double* fe,
       double* pi, double* ei, double* si, double* fi,
       double* pTF, double* eTF, double* sTF, double* fTF )
{
  double x,V,
         Vv,Rv,ev,sv,fv,*qv,qvtot,eev,pev,sev,fev,eiv,piv,siv,fiv,eTFv,pTFv,sTFv,fTFv,
         Vl,Rl,el,sl,fl,*ql,qltot,eel,pel,sel,fel,eil,pil,sil,fil,eTFl,pTFl,sTFl,fTFl;
  int i,c;

  if( Rho < RHO_ZERO ) Rho = RHO_ZERO;
  if( T < T_ZERO ) T = T_ZERO;

  // CASE 1: EOS with Maxwell construction and inside 2 phase region:
  if(Maxwell) {
    if(!((*ionp).MaxwellFlag) || !((*Critical).data.Niso)) { 
      printf( "\nLIB-ERROR in GetAllMaxwellEOSQuantities ---> No Maxwell construction data available !!!\n");
      exit(0);
    }
    // First check if temperature is below the critical point:
    if(T <= ((*Critical).data.Tc)) {    
      // Check if interpolation is possible:
      if(T < (*Critical).data.Tiso[0]) {
        printf( "\nLIB-ERROR in GetAllMaxwellEOSQuantities ---> Temperature below Maxwell isotherm table !!!\n");
        exit(0);      
      }
      // Get density boundaries of 2 phase region by interpolation of pressure in Arrhenius coordinates:
      c = 0;
      while( T >= (*Critical).data.Tiso[c] ) {
        c++;
        if(c == (*Critical).data.Niso) break;
      }
      c = c-1;         
      if(c==(*Critical).data.Niso-1) {
        *p = Linear_Interpol( 1.0/(*Critical).data.Tiso[c], 1.0/(*Critical).data.Tc,
	  		     log10((*Critical).data.Peq[c]), log10((*Critical).data.Pc), 1.0/T );
	  		*p = pow(10.0,*p);
        Rv = Linear_Interpol( (*Critical).data.Peq[c], (*Critical).data.Pc,
	  		     (*Critical).data.Rhov[c], (*Critical).data.Rhoc, *p );
        Rl = Linear_Interpol( (*Critical).data.Peq[c], (*Critical).data.Pc,
	  		     (*Critical).data.Rhol[c], (*Critical).data.Rhoc, *p );
	  	}
	  	else {
        *p = Linear_Interpol( 1.0/(*Critical).data.Tiso[c], 1.0/(*Critical).data.Tiso[c+1],
	  		     log10((*Critical).data.Peq[c]), log10((*Critical).data.Peq[c+1]), 1.0/T );
	  		*p = pow(10.0,*p);
        Rv = Linear_Interpol( (*Critical).data.Peq[c], (*Critical).data.Peq[c+1],
	  		     (*Critical).data.Rhov[c], (*Critical).data.Rhov[c+1], *p );
        Rl = Linear_Interpol( (*Critical).data.Peq[c], (*Critical).data.Peq[c+1],
	  		     (*Critical).data.Rhol[c], (*Critical).data.Rhol[c+1], *p );                               
      }
      // If density is within the 2 phase region, perform linear interpolation of all quantities:
      if( Rho < Rl && Rho > Rv ) {
        qv = dvector(0, (*ionp).Nelements-1);
        ql = dvector(0, (*ionp).Nelements-1);
        *BelowBinodal = 1;
        GetAllEOSQuantities( ionp, qipp, task, Rv, T, &x, &ev, &sv, &fv, qv, &qvtot,
            &pev, &eev, &sev, &fev, &piv, &eiv, &siv, &fiv, &pTFv, &eTFv, &sTFv, &fTFv );        
        GetAllEOSQuantities( ionp, qipp, task, Rl, T, &x, &el, &sl, &fl, ql, &qltot,
            &pel, &eel, &sel, &fel, &pil, &eil, &sil, &fil, &pTFl, &eTFl, &sTFl, &fTFl );        
        Vl = 1.0/ Rl;
        Vv = 1.0/ Rv;
        V =  1.0/ Rho;
        *e = Linear_Interpol( Vl, Vv, el, ev, V );
        *s = Linear_Interpol( Vl, Vv, sl, sv, V ); 
        *f = Linear_Interpol( Vl, Vv, fl, fv, V );
        for(i=0; i<(*ionp).Nelements; i++) q[i] = Linear_Interpol( Vl, Vv, ql[i], qv[i], V );
        *qtot = Linear_Interpol( Vl, Vv, qltot, qvtot, V );
        *pe = Linear_Interpol( Vl, Vv, pel, pev, V );
        *ee = Linear_Interpol( Vl, Vv, eel, eev, V );
        *se = Linear_Interpol( Vl, Vv, sel, sev, V ); 
        *fe = Linear_Interpol( Vl, Vv, fel, fev, V );
        *pi = Linear_Interpol( Vl, Vv, pil, piv, V );
        *ei = Linear_Interpol( Vl, Vv, eil, eiv, V );
        *si = Linear_Interpol( Vl, Vv, sil, siv, V ); 
        *fi = Linear_Interpol( Vl, Vv, fil, fiv, V );   
        *pTF = Linear_Interpol( Vl, Vv, pTFl, pTFv, V );
        *eTF = Linear_Interpol( Vl, Vv, eTFl, eTFv, V );
        *sTF = Linear_Interpol( Vl, Vv, sTFl, sTFv, V ); 
        *fTF = Linear_Interpol( Vl, Vv, fTFl, fTFv, V );                                           
        free_dvector(qv, 0, (*ionp).Nelements-1);
        free_dvector(ql, 0, (*ionp).Nelements-1);             
        return;      
      }
    }
  }

  // CASE 2: EOS without Maxwell construction or outside 2 phase region:
  *BelowBinodal = 0;
  GetAllEOSQuantities( ionp, qipp, task, Rho, T, p, e, s, f, q, qtot,
                       pe, ee, se, fe, pi, ei, si, fi, pTF, eTF, sTF, fTF );
    
  return;
}

//////////////////////////////////////////////////////////////////
// eof.