//////////////////////////////////////////////////////////////////
// user-defined calculations using the FEOS library 
// used by the FEOS table generation tool
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////
// Always check if (*ctab).Niso > 0 before accessing critical table data (*ctab). !!!
//////////////////////////////////////////////////////////////////

#include "FE-02_CALCULATIONS.H"

//////////////////////////////////////////////////////////////////

void UserCalculations( int entity, char* name_in, Qtable* qtab, CriticalDataTable* ctab )
{
  // Calculate Isobaric Expansion data:  
  IsobaricExpansionTable Isotable;
  IsobaricExpansion( entity, &Isotable, qtab, ctab );
  write_isobaricdata( name_in, &Isotable );
  
  return;
}

//////////////////////////////////////////////////////////////////

double Get_Rho_by_TP( int entity, Qtable* qtab, int task, int Maxwell, double t, double p, double x1, double x2 )
{
  // returns density as function of temperature and pressure
  // x1 and x2: appropriate guess for the bracketing densities on isotherm T = t
  
  int j, temp;
  double dx,f,fmid,xmid,rtb;
  double xtemp,prec,ye,ys,yf,*yq,yqtot;
  yq = new double[(*qtab).Nelements];

  if(x1<(*qtab).Rhocalclimit) x1=(*qtab).Rhocalclimit;
  if(x2<(*qtab).Rhocalclimit) x2=(*qtab).Rhocalclimit;

  // get better bracketing densities
  if(x1>x2) { xtemp = x2; x2 = x1; x1 = xtemp; }
  FEOS_Get_EOS( entity, task, Maxwell, x1,t, &temp,&f,&ye,&ys,&yf,yq,&yqtot );  
  FEOS_Get_EOS( entity, task, Maxwell, x2,t, &temp,&fmid,&ye,&ys,&yf,yq,&yqtot );
  if(f<=p) {
    for (j=1;j<=500;j++) {
      xtemp=x1*10.0;
      if(xtemp>=x2) break;
      FEOS_Get_EOS( entity, task, Maxwell, xtemp,t, &temp,&f,&ye,&ys,&yf,yq,&yqtot ); 
      if(f>=p) { x2=xtemp; break; }
      x1=xtemp;
    }
  }
  else {
    for (j=1;j<=500;j++) {
      xtemp=x1*10.0;
      if(xtemp>=x2) break;
      FEOS_Get_EOS( entity, task, Maxwell, xtemp,t, &temp,&f,&ye,&ys,&yf,yq,&yqtot ); 
      if(f<=p) { x2=xtemp; break; }
      x1=xtemp;
    }
  }   

  // find density
  FEOS_Get_EOS( entity, task, Maxwell, x1,t, &temp,&f,&ye,&ys,&yf,yq,&yqtot );  
  FEOS_Get_EOS( entity, task, Maxwell, x2,t, &temp,&fmid,&ye,&ys,&yf,yq,&yqtot );
  f -= p; fmid -= p;
  if (f*fmid >= 0.0) { 
    printf( "\nFE-ERROR in Get_Rho_by_TP ---> Root must be bracketed for bisection !!!\n" );
    exit(0);
  }
  rtb = f < 0.0 ? (dx=x2-x1,x1) : (dx=x1-x2,x2);
  prec = fabs(dx) * eps_getR;
  for (j=1;j<=100;j++) {
    FEOS_Get_EOS( entity, task, Maxwell, xmid=rtb+(dx *= 0.5),t, &temp,&fmid,&ye,&ys,&yf,yq,&yqtot );
    fmid -= p;
    if (fmid <= 0.0) rtb=xmid;
	  if (fabs(dx) < prec || fmid == 0.0) { delete yq; return rtb; }
  }
  printf("\nFE-ERROR in Get_Rho_by_TP ---> Too many bisections !!!\n"); 
  delete yq;  
  exit(0);
  return 0.0;
}

//////////////////////////////////////////////////////////////////

void IsobaricExpansion( int entity, IsobaricExpansionTable* data, Qtable* qtab, CriticalDataTable* ctab ) 
{ 
  // Calculate densities, thermal expansion coefficient, enthalpy and heat capacity 
  // for isobaric expansion (P=0) (only possible without Maxwell construction)
  
  double t, dt, r, h, Pma, Rma, Pmi, Rmi,
         T1, T2, DT, R1, R2, H1, H2,
         p, e, f, s, *q, qtot, alpha, cp;
  int j, temp;
  q = new double[(*qtab).Nelements];

  (*data).MaxT = 5.1704304e-1;
  (*data).MinT = (*qtab).Tcalclimit;
  (*data).NT = 21;

  (*data).Tiso = dvector(0,(*data).NT-1);
  (*data).Rho0 = dvector(0,(*data).NT-1);
  (*data).P = dvector(0,(*data).NT-1);
  (*data).alpha = dvector(0,(*data).NT-1);
  (*data).H = dvector(0,(*data).NT-1);
  (*data).Cp = dvector(0,(*data).NT-1);

  printf( "\nCalculate isobaric expansion data along P ~ 0 bar:\n Tstart = %e eV\n Tend = %e eV\n", (*data).MinT, (*data).MaxT );
  if((*ctab).Niso>0) printf( " Calculation only possible without Maxwell construction!\n" ); 
  (*data).Niso = 0; 
  dt = ((*data).MaxT - (*data).MinT) / ((*data).NT-1);
  printf(" T [eV]     Rho [g/cm^3] Alpha [1/eV] H [erg/g]    P [dyne/cm^2] Cp [erg/eVg]\n");
  for(j=0; j<(*data).NT; j++) {
    (*data).Tiso[j] = t = (*data).MinT + j * dt;
    DT = ( t > 0.0 ) ? ( t * epsDT ) : ( 1.0e-4 * epsDT );
    T1 = t - DT;
    T2 = t + DT;
    // Pmin for T2 has to be <0 to assure quasiisobaric expansion along p=0
    FEOS_Get_Pmin_Pmax( entity, T2, &Rmi, &Rma, &Pmi, &Pma );    
    if(Pmi<=0.0) {
      // Case T=0 has to be treated separately:
      if(t==0.0) {
	      // Get densities for t and T2
	      R2 = Get_Rho_by_TP( entity, qtab, 0, 0, T2, 0.0, Rmi*0.99, (*qtab).RhoRef*10);
	      FEOS_Get_Pmin_Pmax( entity, t, &Rmi, &Rma, &Pmi, &Pma );
	      (*data).Rho0[j] = r = Get_Rho_by_TP( entity, qtab, 0, 0, t, 0.0, Rmi*0.99, (*qtab).RhoRef*10);
	      // Get pressure for t and enthalpy for t and T2
        FEOS_Get_EOS( entity, 0, 0, R2, T2, &temp, &p, &e, &s, &f, q, &qtot );
	      H2 = e + ( p / R2 );
	      FEOS_Get_EOS( entity, 0, 0, r, t, &temp, &p, &e, &s, &f, q, &qtot );
	      (*data).P[j] = p;
	      (*data).H[j] = h = e + ( p / r );
	      // Calculate thermal expansion coefficient
	      (*data).alpha[j] = alpha = - (R2 - r) / (DT * r);
	      // Calculate isobaric heat capacity
	      (*data).Cp[j] = cp = (H2 - h) / (DT * eV2Kelvin);
      }
      // Case T>0:
      else {
	      // Get densities for t, T1 and T2
	      R2 = Get_Rho_by_TP( entity, qtab, 0, 0, T2, 0.0, Rmi*0.99, (*qtab).RhoRef*10 );
	      FEOS_Get_Pmin_Pmax( entity, T1, &Rmi, &Rma, &Pmi, &Pma );
	      R1 = Get_Rho_by_TP( entity, qtab, 0, 0, T1, 0.0, Rmi*0.99, (*qtab).RhoRef*10 );
	      FEOS_Get_Pmin_Pmax( entity, t, &Rmi, &Rma, &Pmi, &Pma );
	      (*data).Rho0[j] = r = Get_Rho_by_TP( entity, qtab, 0, 0, t, 0.0, Rmi*0.99, (*qtab).RhoRef*10 );
	      // Get pressure for t and enthalpy for t and T2
	      FEOS_Get_EOS( entity, 0, 0, R2, T2, &temp, &p, &e, &s, &f, q, &qtot );
	      H2 = e + ( p / R2 );
	      FEOS_Get_EOS( entity, 0, 0, R1, T1, &temp, &p, &e, &s, &f, q, &qtot );
	      H1 = e + ( p / R1 );
	      FEOS_Get_EOS( entity, 0, 0, r, t, &temp, &p, &e, &s, &f, q, &qtot );
	      (*data).P[j] = p;
	      (*data).H[j] = h = e + ( p / r );
	      // Calculate thermal expansion coefficient
	      (*data).alpha[j] = alpha = - (R2 - R1) / (2.0 * DT * r);
	      // Calculate isobaric heat capacity
	      (*data).Cp[j] = cp = (H2 - H1) / (2.0 * DT);
      }
      printf(" %.4e %.6e %+.5e %+.5e %+.6e %+.5e\n",t,r,alpha,h,p,cp );
      (*data).Niso += 1;
    }
    else 
    {
      if (t==0.0) printf("Isobaric expansion data cannot be calculated.\n");
      else
      {
	      (*data).Rho0[j] = r = (*data).P[j] = p = (*data).H[j] = h = (*data).alpha[j] = alpha = (*data).Cp[j] = cp = 0.0;
	      printf(" %.4e %.6e      ---          ---     %+.6e      ---\n",t,r,p );
        (*data).Niso += 1;
      }
      break;
    }
  }

  printf("Done.\n");
  delete q;
  return;
}

//////////////////////////////////////////////////////////////////

void write_isobaricdata( char* name_in, IsobaricExpansionTable* data )
{ 
  // write isobaric expansion data to .isobaric.dat file
  
  FILE* h;
  int j;
  char name[STRSIZE];
  sprintf( name, "%s.%s", name_in, ISOBARIC_SUFFIX );
  printf( "\nWrite isobaric expansion data (%s)...",name );
  h = fopen( name, "w" );
  fprintf( h, "# Calculated isobaric expansion data (P ~= 0) from %.2f to %.2f Kelvin:\n", 
	   (*data).MinT*eV2Kelvin, (*data).MaxT*eV2Kelvin );
  fprintf( h, "# T [K]       Rho [g/cm^3]  P [bar]        Alpha [1/K]    H [J/g]        Cp [J/gK]\n" );
  for(j=0;j<(*data).Niso;j++) {
    if(j==(*data).Niso-1 && (*data).alpha[j]==0.0 && (*data).Cp[j]==0.0 && (*data).H[j]==0.0)
	    fprintf( h, "%e  %e  %+e       ---            ---            ---\n",
	    (*data).Tiso[j]*eV2Kelvin,(*data).Rho0[j],(*data).P[j]*cgs2Bar );
    else fprintf( h, "%e  %e  %+e  %+e  %+e  %+e\n",
	    (*data).Tiso[j]*eV2Kelvin,(*data).Rho0[j],(*data).P[j]*cgs2Bar,
	    (*data).alpha[j]/eV2Kelvin,(*data).H[j]*cgs2Joule,(*data).Cp[j]*cgs2Joule/eV2Kelvin );
  }
  fprintf( h, "\n# Data in T-Rho-plane" );
  fprintf( h, "\n# T [Kelvin]  Rho [g/cm³]\n" );
  for(j=0;j<(*data).Niso;j++) {
    fprintf( h, "%e  %e\n", (*data).Tiso[j]*eV2Kelvin, (*data).Rho0[j] );
  }
  fprintf( h, "# eof.\n" );
  fclose( h);
  printf(" done.\n" );
  
  free_dvector( (*data).Tiso,0,(*data).NT-1 ); 
  free_dvector( (*data).Rho0,0,(*data).NT-1 );
  free_dvector( (*data).P,0,(*data).NT-1 );
  free_dvector( (*data).alpha,0,(*data).NT-1 );
  free_dvector( (*data).H,0,(*data).NT-1 );
  free_dvector( (*data).Cp,0,(*data).NT-1 );
  return;
}

//////////////////////////////////////////////////////////////////
// eof.