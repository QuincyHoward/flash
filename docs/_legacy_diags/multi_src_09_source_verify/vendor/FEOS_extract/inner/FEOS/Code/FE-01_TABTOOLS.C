//////////////////////////////////////////////////////////////////
// service routines for handling tables 
// used by the FEOS table generation tool
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#include "FE-01_TABTOOLS.H"

//////////////////////////////////////////////////////////////////

void getPointDensity( readfile *rf, int *density, int *total, char *type_name )
{
  // read desired distribution from parameter file
  
  char str[STRSIZE];
  int c;
  *total = 1;
  for( c = -MAXRATIO; c <=MAXRATIO; c++ ) {
    sprintf( str, "%s%d",type_name,c);
    density[c+MAXRATIO] = atoi( (*rf).setget( (char*)"Q-table", str ) );
    *total += (density[c+MAXRATIO]);   // don't count overlapping points
    if(density[c+MAXRATIO]<0){
   	  printf("\nME-ERROR in getPointDensity ---> %s = %d, %s must be positive !!!\n", str, density[c+MAXRATIO], str);    
      exit(0);    
    }    
  }
  return;
}

//////////////////////////////////////////////////////////////////

void makeRTPointArray( int *density, double *array, double Qnorm, double Qstart )
{
  // set points for RT grid
  
  int n,c,i,tc;
  double q,mult;
  array[0] = Qstart;
  q = pow(10.0, -MAXRATIO-1 ) * Qnorm;
  tc = 1;
  for( c = -MAXRATIO; c <= MAXRATIO; c++ ) {
    n = density[c+MAXRATIO];
    if( n>0 ) {
      mult = pow( 10.0, 1.0/n );
      for( i = 1; i<= n; i++ ) { 
	      array[tc] = q;
	      tc++;
    	  q *= mult;
      }
    }
    else q *= 10.0;
  }
  return;
}

//////////////////////////////////////////////////////////////////

void write_criticaldata( char* name_in, CriticalDataTable* ctable, int MaxwellFlag, double Atot, double Xtot )
{ 
  // write binodal, spinodal, boiling- and cp-data to .critical.dat file
  
  FILE* h;
  int j,i;
  double Amean = Atot/Xtot;
  char name[STRSIZE];
  sprintf( name, "%s.%s", name_in, CRITICAL_SUFFIX );
  printf( "\nWrite critical data table (%s)...",name );
  h = fopen( name, "w" );
  fprintf( h, "# Critical point: Tc = %.2f K, Pc = %.2f bar, Rhoc = %.4f g/cm³,\n", 
	   (*ctable).Tc*eV2Kelvin, (*ctable).Pc*cgs2Bar, (*ctable).Rhoc );
  fprintf( h, "#                 Hc = %.2f kJ/g, Sc/R = %.4f, Zc = %.2f\n\n", 
	   (*ctable).Hc*cgs2Joule*1.0e-3, (*ctable).Sc*Amean/GAS_CONSTANT, (*ctable).Zc );
  if(MaxwellFlag==2) 
    fprintf( h, "# Two-phase-boundary (binodal) calculated by finding equal areas under/over pressure-loops! \n\n" ); 
  else 
    fprintf( h, "# Two-phase-boundary (binodal) calculated by finding densities with equal pressure and Gibbs free energy! \n\n" );
  if((*ctable).Tb) fprintf( h, "# Boiling temperature: Tb = %.2f K \n\n", (*ctable).Tb*eV2Kelvin );
  else fprintf( h, "# Boiling temperature could not be calculated! \n\n" );

  fprintf( h, "# Number of calculated isotherms below cp: Niso = %d \n\n", (*ctable).Niso );
  i = 0;
  fprintf( h , "# Temperatures in Kelvin:\n# " );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e", (*ctable).Tiso[j]*eV2Kelvin );
    if(j!=(*ctable).Niso-1) fprintf( h, ", " );
    if(++i==6&&j!=(*ctable).Niso-1) { i = 0; fprintf( h, "\n# " ); }
  }
  fprintf( h, "\n" );

  fprintf( h, "\n# Check P_sat = P_vap = P_liq and G_vap = G_liq for good accuracy of binodal:" );
  fprintf( h, "\n# T [Kelvin]  Rho_vap [g/cm³]  Rho_liq [g/cm³]  P_sat [bar]  P_vap [bar]  P_liq [bar]  G_vap [kJ/g]  G_liq [kJ/g]\n" );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e  %e  %e  %e  %+e  %+e  %+e  %+e\n", (*ctable).Tiso[j]*eV2Kelvin, (*ctable).Rhov[j], (*ctable).Rhol[j],
	     (*ctable).Peq[j]*cgs2Bar, (*ctable).Pv[j]*cgs2Bar, (*ctable).Pl[j]*cgs2Bar, (*ctable).Gv[j]*cgs2Joule*1.0e-3 , (*ctable).Gl[j]*cgs2Joule*1.0e-3 );
  }

  fprintf( h, "\n# Binodal in Rho-P-plane" );
  fprintf( h, "\n# Rho [g/cm³]  P_sat [bar]\n" );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e  %+e\n", (*ctable).Rhov[j], (*ctable).Peq[j]*cgs2Bar );
  }
  fprintf( h, "%e  %+e\n", (*ctable).Rhoc, (*ctable).Pc*cgs2Bar );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e  %+e\n", (*ctable).Rhol[(*ctable).Niso-1-j], (*ctable).Peq[(*ctable).Niso-1-j]*cgs2Bar );
  }

  fprintf( h, "\n# Spinodal in Rho-P-plane" );
  fprintf( h, "\n# Rho [g/cm³]  P_sat [bar]\n" );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e  %+e\n", (*ctable).Rhomax[j], (*ctable).Pmax[j]*cgs2Bar );
  }
  fprintf( h, "%e  %+e\n", (*ctable).Rhoc, (*ctable).Pc*cgs2Bar );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e  %+e\n", (*ctable).Rhomin[(*ctable).Niso-1-j], (*ctable).Pmin[(*ctable).Niso-1-j]*cgs2Bar );
  }

  fprintf( h, "\n# Binodal in T-Rho-plane" );
  fprintf( h, "\n# T [Kelvin]  Rho [g/cm³]\n" );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e  %e\n", (*ctable).Tiso[j]*eV2Kelvin, (*ctable).Rhov[j] );
  }
  fprintf( h, "%e  %e\n", (*ctable).Tc*eV2Kelvin, (*ctable).Rhoc );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e  %e\n", (*ctable).Tiso[(*ctable).Niso-1-j]*eV2Kelvin, (*ctable).Rhol[(*ctable).Niso-1-j] );
  }

  fprintf( h, "\n# Spinodal in T-Rho-plane" );
  fprintf( h, "\n# T [Kelvin]  Rho [g/cm³]\n" );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e  %e\n", (*ctable).Tiso[j]*eV2Kelvin, (*ctable).Rhomax[j] );
  }
  fprintf( h, "%e  %e\n", (*ctable).Tc*eV2Kelvin, (*ctable).Rhoc );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e  %e\n", (*ctable).Tiso[(*ctable).Niso-1-j]*eV2Kelvin, (*ctable).Rhomin[(*ctable).Niso-1-j] );
  }

  fprintf( h, "\n# Diamener curve in T-Rho-plane" );
  fprintf( h, "\n# T [Kelvin]  1/2*Rho_liq+1/2*Rho_vap [g/cm³]\n" );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e  %e\n", (*ctable).Tiso[j]*eV2Kelvin, 0.5*((*ctable).Rhov[j]+(*ctable).Rhol[j]) );
  }
  fprintf( h, "%e  %e\n", (*ctable).Tc*eV2Kelvin, (*ctable).Rhoc );

  fprintf( h, "\n# Binodal in T-H-plane" );
  fprintf( h, "\n# T [Kelvin]  H [kJ/g]\n" );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e  %+e\n", (*ctable).Tiso[j]*eV2Kelvin, (*ctable).Hv[j]*cgs2Joule*1.0e-3 );
  }
  fprintf( h, "%e  %+e\n", (*ctable).Tc*eV2Kelvin, (*ctable).Hc*cgs2Joule*1.0e-3 );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e  %+e\n", (*ctable).Tiso[(*ctable).Niso-1-j]*eV2Kelvin, (*ctable).Hl[(*ctable).Niso-1-j]*cgs2Joule*1.0e-3 );
  }

  fprintf( h, "\n# Evaporation heat in T-DeltaH-plane" );
  fprintf( h, "\n# T [Kelvin]  DeltaH [kJ/g]\n" );
  for(j=0;j<(*ctable).Niso;j++) {
    fprintf( h, "%e  %+e\n", (*ctable).Tiso[j]*eV2Kelvin, ((*ctable).Hv[j]-(*ctable).Hl[j])*cgs2Joule*1.0e-3 );
  }
  fprintf( h, "%e  %+e\n", (*ctable).Tc*eV2Kelvin, 0.0 );

  fprintf( h, "\n# Saturation curve in Arrhenius coordinates" );
  fprintf( h, "\n# 1/T [T in Kelvin]  log10(P_sat) [P_sat in bar]\n" );
  fprintf( h, "%e  %+e\n", 1/((*ctable).Tc*eV2Kelvin), log10((*ctable).Pc*cgs2Bar) );
  for(j=0;j<(*ctable).Niso-1;j++) {
    if((*ctable).Peq[(*ctable).Niso-1-j]>0.0) fprintf( h, "%e  %+e\n", 1/((*ctable).Tiso[(*ctable).Niso-1-j]*eV2Kelvin), log10((*ctable).Peq[(*ctable).Niso-1-j]*cgs2Bar) );
  }

  fprintf( h, "\n# Compressibility factor in T-Z-plane" );
  fprintf( h, "\n# T [Kelvin]  Z\n" );
  for(j=0;j<(*ctable).Niso;j++) {
    if((*ctable).Tiso[j]>0.0) fprintf( h, "%e  %+e\n", (*ctable).Tiso[j]*eV2Kelvin, (*ctable).Zv[j] );
  }
  fprintf( h, "%e  %+e\n", (*ctable).Tc*eV2Kelvin, (*ctable).Zc );
  for(j=0;j<(*ctable).Niso;j++) {
    if((*ctable).Tiso[(*ctable).Niso-1-j]>0.0) fprintf( h, "%e  %+e\n", (*ctable).Tiso[(*ctable).Niso-1-j]*eV2Kelvin, (*ctable).Zl[(*ctable).Niso-1-j] );
  }

  fprintf( h, "\n# Compressibility factor in P-Z-plane" );
  fprintf( h, "\n# P_sat [bar]  Z\n" );
  for(j=0;j<(*ctable).Niso;j++) {
    if((*ctable).Tiso[j]>0.0) fprintf( h, "%e  %+e\n", (*ctable).Peq[j]*cgs2Bar, (*ctable).Zv[j] );
  }
  fprintf( h, "%e  %+e\n", (*ctable).Pc*cgs2Bar, (*ctable).Zc );
  for(j=0;j<(*ctable).Niso;j++) {
    if((*ctable).Tiso[(*ctable).Niso-1-j]>0.0) fprintf( h, "%e  %+e\n", (*ctable).Peq[(*ctable).Niso-1-j]*cgs2Bar, (*ctable).Zl[(*ctable).Niso-1-j] );
  }

  fprintf( h, "# eof.\n" );
  fclose( h);
  printf(" done.\n" );
  return;
}

//////////////////////////////////////////////////////////////////

void write_FEOS_format( char* name_in, Qtable* table)
{
  // FEOS EOS format
  // indices start at 0
  //
  // with Pressure, Energy, Free Energy, Entropy, Charge states, 
  //      EOS paramters
  //
  // FEOS units are cgs (+ eV for temperature)
  
  double FileVersion = 12.06;
  int i,j,k,count,
    NR = (*table).NRho-1,
    NT = (*table).NT-1,
    Nelements = (*table).Nelements-1;
  FILE* h;
  char name[STRSIZE];  

  sprintf( name,"%s.%s",name_in,"feos" );
  printf( "\nWrite FEOS table format (%s):\n", name );
  if ((h = fopen(name,"w")) == NULL) {
    printf("\nFE-ERROR in write_FEOS_format ---> Error occured while opening file !!!\n");
    exit(0);
  }

  // Print EOS parameters:
  fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",FileVersion,SF_TRENN,double(NR+1),SF_TRENN,double(NT+1),SF_TRENN,double(Nelements+1),SF_TRENN,(*table).Tcalclimit);
  fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",(*table).Rhocalclimit,SF_TRENN,(*table).RhoRef,SF_TRENN,(*table).TRef,SF_TRENN,(*table).BulkModulusRef,SF_TRENN,double((*table).SESAMEnumber));
  fprintf(h,"\n");
  fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",(*table).ElectronOffset,SF_TRENN,(*table).IonOffset,SF_TRENN,(*table).Ecoh,SF_TRENN,(*table).softsphere_n,SF_TRENN,(*table).softsphere_m);
  fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",(*table).softsphere_A,SF_TRENN,(*table).softsphere_B,SF_TRENN,(*table).Atot,SF_TRENN,(*table).Ztot,SF_TRENN,(*table).Xtot);
  fprintf(h,"\n");
  //
  count = 0;
  //
  for(k=0;k<=Nelements;k++ ) {
    fprintf(h,"%15.8le", (*table).A[k] );
    if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }
  for(k=0;k<=Nelements;k++ ) {
    fprintf(h,"%15.8le", (*table).Z[k] );
    if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }   
  for(k=0;k<=Nelements;k++ ) {
    fprintf(h,"%15.8le", (*table).X[k] );
    if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }
  
  // Print densities and temperatures:      
  for(i=0;i<=NR;i++ ) {
    fprintf(h,"%15.8le", (*table).Rho[i] );
    if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }
  for(j=0;j<=NT;j++ ) {
    fprintf(h,"%15.8le", (*table).T[j] );
    if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }        

  // Print total EOS: 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).P[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).E[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).S[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).F[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }  

  // Print electronic EOS: 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Pe[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Ee[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Se[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Fe[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }  

  // Print ionic EOS: 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Pi[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Ei[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Si[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Fi[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }  

  // Print pure Thomas-Fermi EOS: 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).PTF[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).ETF[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).STF[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).FTF[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }  

  // Print charge states: 
  for(j=0;j<=NT;j++)
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Qtot[i][j] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) 
      for(k=0;k<=Nelements;k++) {
      fprintf(h,"%15.8le", (*table).Q[i][j][k] );
			if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
      }  
                
  fclose(h);

  printf(" Table size (densities x temperatures): %d x %d\n Table boundaries (density, temperature):\n", NR+1, NT+1);
  printf("  (%e g/cm^3, %e eV) ...\n", (*table).Rho[0], (*table).T[0]);
  if(NR>1 && NT<2) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[1], (*table).T[0]);
  else if(NR<2 && NT>1) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[0], (*table).T[1]);
  else if(NR>1 && NT>1) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[1], (*table).T[1]);
  printf("  ... (%e g/cm^3, %e eV)\n", (*table).Rho[NR], (*table).T[NT]);  
  printf("Done.\n");
    
  return;   
}  
  
//////////////////////////////////////////////////////////////////

void write_mexport_format( char* name_in, Qtable* table)
{
  // SESAME mexport format
  // indices start at 0
  //
  // with Pressure, Energy, Free Energy
  //
  // SESAME units are
  //
  // Pressure in GPa
  // energy in MJ/kg
  // density Mg/m3
  // temperature in Kelvin
  //

  double rhosolid = (*table).RhoRef;
  double Amat = (*table).Atot/(*table).Xtot;
  double Zmat = (*table).Ztot/(*table).Xtot;
  double Bulkmat = (*table).BulkModulusRef;
  int matnumber = (*table).SESAMEnumber;
  
  time_t current;
  struct tm *timeptr;
  
   current = time(NULL);
   timeptr = localtime(&current);

  int i,j,count,
    NR = (*table).NRho-1,
    NT = (*table).NT-1;
  FILE* h;
  char name[STRSIZE];
  char linea[81];
  char control[6]="00000";
  //
  sprintf( name,"%s.%s",name_in,"mexport" );
  printf( "\nWrite SESAME mexport table format (%s):\n", name );
  if ((h = fopen(name,"w")) == NULL) {
    printf("\nFE-ERROR in write_mexport_format ---> Error occured while opening file !!!\n");
    exit(0);
  }

  fprintf(h,"%2d%6d%6d%6d   r%9d%9d%4d%34d\n",0,matnumber,101,160,0,0,1,1);
  sprintf(linea,"material. %s (Zmean=%.1f, Amean=%.2f) /source. feos /date %04d%02d%02d%02d%02d",name_in,Zmat,Amat,timeptr->tm_year + 1900, timeptr->tm_mon+1, timeptr->tm_mday,timeptr->tm_hour,timeptr->tm_min);
  fprintf(h,"%s",linea);
  for (int i=strlen(linea);i<80;i++) fprintf(h," ");
  fprintf(h,"\n");
  sprintf(linea,"/refs. none /comp. LULI /codes. FEOS /");
  fprintf(h,"%s",linea);
  for (int i=strlen(linea);i<80;i++) fprintf(h," ");
  fprintf(h,"\n");
  fprintf(h,"%2d%6d%6d%6d   r%9d%9d%4d%34d\n",1,matnumber,102,80,0,0,1,1);
  sprintf(linea,"contact: tommaso.vinci@polytechnique.edu");
  fprintf(h,"%s",linea);
  for (int i=strlen(linea);i<80;i++) fprintf(h," ");
  fprintf(h,"\n");
  fprintf(h,"%2d%6d%6d%6d   r%9d%9d%4d%34d\n",1,matnumber,201,5,0,0,1,1);
  fprintf(h,"%15.8le%15.8le%15.8le%15.8le%15.8le11100\n",Zmat,Amat,rhosolid,Bulkmat/1.e10,0.);


  //  
  //  Writing Total EOS 301 
  //  
  fprintf(h,"%2d%6d%6d%6d   r%9d%9d%4d%34d\n",1,matnumber,301,2+(NR+1)+(NT+1)+3*(NR+1)*(NT+1),0,0,1,1);
  fprintf(h,"%15.8le%15.8le",double(NR+1),double(NT+1));
  //
  // Rho and T vectors:
  //  
  count = 0;
  if (NR+1==0) control[count++]='0'; else control[count++]='1';
  if (NT+1==0) control[count++]='0'; else control[count++]='1';
  for(i=0;i<=NR;i++ ) {
    fprintf(h,"%15.8e", (*table).Rho[i]*cgs2ses_rho );
    if ( (*table).Rho[i]*cgs2ses_rho == 0.) control[count%5]='0'; else control[count%5]='1';
    if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
  }  
  for(j=0;j<=NT;j++ ) {
    fprintf(h,"%15.8le", (*table).T[j]*cgs2ses_t ); 
    if ( (*table).T[j]*cgs2ses_t == 0.) control[count%5]='0'; else control[count%5]='1';
    if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
  } 

  for(j=0;j<=NT;j++)      // pressure :
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).P[i][j]*cgs2ses_p );
			if ( (*table).P[i][j]*cgs2ses_p == 0.) control[count%5]='0'; else control[count%5]='1';
			if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
    }  
  
  for(j=0;j<=NT;j++)   // energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).E[i][j]*cgs2ses_e );
			if ( (*table).E[i][j]*cgs2ses_e == 0.) control[count%5]='0'; else control[count%5]='1';
			if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
    }  
  
  for(j=0;j<=NT;j++)  // free energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).F[i][j]*cgs2ses_e );
			if ( (*table).F[i][j]*cgs2ses_e == 0.) control[count%5]='0'; else control[count%5]='1';
			if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
    }

  if (count%5 != 0) {
		for (i=(count%5);i<5;i++) {
				fprintf(h,"               ");
				control[i]='0';
    }
	  fprintf(h,"%5s\n",control);    
  }
    
  //  
  //  Writing Electron EOS 304 
  //  
  fprintf(h,"%2d%6d%6d%6d   r%9d%9d%4d%34d\n",1,matnumber,304,2+(NR+1)+(NT+1)+3*(NR+1)*(NT+1),0,0,1,1);
  fprintf(h,"%15.8le%15.8le",double(NR+1),double(NT+1));
  count = 0;
  if (NR+1==0) control[count++]='0'; else control[count++]='1';
  if (NT+1==0) control[count++]='0'; else control[count++]='1';
  for(i=0;i<=NR;i++ ) {
    fprintf(h,"%15.8e", (*table).Rho[i]*cgs2ses_rho );
    if ( (*table).Rho[i]*cgs2ses_rho == 0.) control[count%5]='0'; else control[count%5]='1';
    if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
  }  
  for(j=0;j<=NT;j++ ) {
    fprintf(h,"%15.8le", (*table).T[j]*cgs2ses_t); 
    if ( (*table).T[j]*cgs2ses_t == 0.) control[count%5]='0'; else control[count%5]='1';
    if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
  } 
    
  for(j=0;j<=NT;j++)      // pressure :
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Pe[i][j]*cgs2ses_p );
			if ( (*table).Pe[i][j]*cgs2ses_p == 0.) control[count%5]='0'; else control[count%5]='1';
			if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
    }  
  
  for(j=0;j<=NT;j++)   // energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Ee[i][j]*cgs2ses_e );
			if ( (*table).Ee[i][j]*cgs2ses_e == 0.) control[count%5]='0'; else control[count%5]='1';
			if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
    }  
  
  for(j=0;j<=NT;j++)  // free energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).F[i][j]*cgs2ses_e );
			if ( (*table).F[i][j]*cgs2ses_e == 0.) control[count%5]='0'; else control[count%5]='1';
			if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
    }

  if (count%5 != 0) {
		for (i=(count%5);i<5;i++) {
				fprintf(h,"               ");
				control[i]='0';
    }
	  fprintf(h,"%5s\n",control);    
  }

  //  
  //  Writing Ions EOS 305 
  //  
  fprintf(h,"%2d%6d%6d%6d   r%9d%9d%4d%34d\n",1,matnumber,305,2+(NR+1)+(NT+1)+3*(NR+1)*(NT+1),0,0,1,1);
  fprintf(h,"%15.8le%15.8le",double(NR+1),double(NT+1));
  count = 0;
  if (NR+1==0) control[count++]='0'; else control[count++]='1';
  if (NT+1==0) control[count++]='0'; else control[count++]='1';
  for(i=0;i<=NR;i++ ) {
    fprintf(h,"%15.8e", (*table).Rho[i]*cgs2ses_rho );
    if ( (*table).Rho[i]*cgs2ses_rho == 0.) control[count%5]='0'; else control[count%5]='1';
    if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
  }  
  for(j=0;j<=NT;j++ ) {
    fprintf(h,"%15.8le", (*table).T[j]*cgs2ses_t ); 
    if ( (*table).T[j]*cgs2ses_t == 0.) control[count%5]='0'; else control[count%5]='1';
    if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
  } 
    
  for(j=0;j<=NT;j++)      // pressure :
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Pi[i][j]*cgs2ses_p );
			if ( (*table).Pi[i][j]*cgs2ses_p == 0.) control[count%5]='0'; else control[count%5]='1';
			if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
    }  
  
  for(j=0;j<=NT;j++)   // energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Ei[i][j]*cgs2ses_e );
			if ( (*table).Ei[i][j]*cgs2ses_e == 0.) control[count%5]='0'; else control[count%5]='1';
			if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
    }  
  
  for(j=0;j<=NT;j++)  // free energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).F[i][j]*cgs2ses_e );
			if ( (*table).F[i][j]*cgs2ses_e == 0.) control[count%5]='0'; else control[count%5]='1';
			if(++count%5) fprintf(h,"%s",SF_TRENN); else fprintf(h,"%5s\n",control);
    }

  if (count%5 != 0) {
		for (i=(count%5);i<5;i++) {
				fprintf(h,"               ");
				control[i]='0';
    }
	  fprintf(h,"%5s\n",control);    
  }
  
  fprintf(h," 2                                                                             2\n");
  
  fclose(h);

  printf(" Table size (densities x temperatures): %d x %d\n Table boundaries (density, temperature):\n", NR+1, NT+1);
  printf("  (%e g/cm^3, %e eV) ...\n", (*table).Rho[0], (*table).T[0]);
  if(NR>1 && NT<2) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[1], (*table).T[0]);
  else if(NR<2 && NT>1) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[0], (*table).T[1]);
  else if(NR>1 && NT>1) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[1], (*table).T[1]);
  printf("  ... (%e g/cm^3, %e eV)\n", (*table).Rho[NR], (*table).T[NT]);  
  printf("Done.\n");
  
  return;   
}

//////////////////////////////////////////////////////////////////

void write_301_format( char* name_in, Qtable* table)
{
  // SESAME 301 standard format
  // indices start at 0
  //
  // with Pressure, Energy, Charge State
  //
  // SESAME units are
  //
  // Pressure in GPa
  // energy in MJ/kg
  // density Mg/m3
  // temperature in Kelvin

  double rhosolid = (*table).RhoRef;
  int matnumber = (*table).SESAMEnumber;

  int i,j,count,
    NR = (*table).NRho-1,
    NT = (*table).NT-1;
  FILE* h;
  char name[STRSIZE];
  //
  sprintf( name,"%s.%s",name_in,SES_301_SUFFIX );
  printf( "\nWrite SESAME table format (%s):\n",name );
  if ((h = fopen(name,"w")) == NULL) {
    printf("\nFE-ERROR in write_301_format ---> Error occured while opening file !!!\n");
    exit(0);
  }
  
  fprintf(h," %04d0301      %15.8le%15.8le%15.8le\n",
	  matnumber,rhosolid,double(NR+1),double(NT+1) );
  //
  // Rho and T vectors:
  //  
  count = 0;
  for(i=0;i<=NR;i++ ) {
    fprintf(h,"%15.8le", (*table).Rho[i]*cgs2ses_rho );
    if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }  
  for(j=0;j<=NT;j++ ) {
    fprintf(h,"%15.8le", (*table).T[j]*cgs2ses_t ); 
    if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  } 

  for(j=0;j<=NT;j++)      // pressure
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).P[i][j]*cgs2ses_p );
      if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }  
  
  for(j=0;j<=NT;j++)   // energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).E[i][j]*cgs2ses_e );
      if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }  
  
  for(j=0;j<=NT;j++)  // free energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).F[i][j]*cgs2ses_e );
      if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }

  fclose(h);
  
  printf(" Table size (densities x temperatures): %d x %d\n Table boundaries (density, temperature):\n", NR+1, NT+1);
  printf("  (%e g/cm^3, %e eV) ...\n", (*table).Rho[0], (*table).T[0]);
  if(NR>1 && NT<2) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[1], (*table).T[0]);
  else if(NR<2 && NT>1) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[0], (*table).T[1]);
  else if(NR>1 && NT>1) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[1], (*table).T[1]);
  printf("  ... (%e g/cm^3, %e eV)\n", (*table).Rho[NR], (*table).T[NT]);  
  printf("Done.\n");
  
  return;   
}

//////////////////////////////////////////////////////////////////

void write_304_format( char* name_in, Qtable* table)
{
  // SESAME 304 standard format
  // indices start at 0
  //
  // with Pressure, Energy, Charge State
  //
  // SESAME units are
  //
  // Pressure in GPa
  // energy in MJ/kg
  // density Mg/m3
  // temperature in Kelvin

  double rhosolid = (*table).RhoRef;
  int matnumber = (*table).SESAMEnumber;
  int i,j,count,
    NR = (*table).NRho-1,
    NT = (*table).NT-1;
  FILE* h;
  char name[STRSIZE];

  //
  sprintf( name,"%s.%s",name_in,SES_304_SUFFIX );
  printf( "\nWrite SESAME table format for electrons (%s):\n",name );
  if ((h = fopen(name,"w")) == NULL) {
    printf("\nFE-ERROR in write_304_format ---> Error occured while opening file !!!\n");
    exit(0);
  }
  fprintf(h," %04d0304      %15.8le%15.8le%15.8le\n",
	  matnumber,rhosolid,double(NR+1),double(NT+1) );
  //
  // Rho and T vectors:
  //  
  count = 0;
  for(i=0;i<=NR;i++ ) {
    fprintf(h,"%15.8e", (*table).Rho[i]*cgs2ses_rho );
    if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }  
  for(j=0;j<=NT;j++ ) {
    fprintf(h,"%15.8le", (*table).T[j]*cgs2ses_t ); 
    if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  } 

  for(j=0;j<=NT;j++)      // pressure :
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Pe[i][j]*cgs2ses_p );
      if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }  
  
  for(j=0;j<=NT;j++)   // energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Ee[i][j]*cgs2ses_e );
      if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }  
  
  for(j=0;j<=NT;j++)  // free energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Fe[i][j]*cgs2ses_e );
      if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  fclose(h);

  printf(" Table size (densities x temperatures): %d x %d\n Table boundaries (density, temperature):\n", NR+1, NT+1);
  printf("  (%e g/cm^3, %e eV) ...\n", (*table).Rho[0], (*table).T[0]);
  if(NR>1 && NT<2) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[1], (*table).T[0]);
  else if(NR<2 && NT>1) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[0], (*table).T[1]);
  else if(NR>1 && NT>1) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[1], (*table).T[1]);
  printf("  ... (%e g/cm^3, %e eV)\n", (*table).Rho[NR], (*table).T[NT]);  
  printf("Done.\n");
  
  return;   
}

//////////////////////////////////////////////////////////////////

void write_305_format( char* name_in, Qtable* table)
{
  // SESAME 305 standard format
  // indices start at 0
  //
  // with Pressure, Energy, Charge State
  //
  // SESAME units are
  //
  // Pressure in GPa
  // energy in MJ/kg
  // density Mg/m3
  // temperature in Kelvin

  double rhosolid = (*table).RhoRef;
  int matnumber = (*table).SESAMEnumber;
  int i,j,count,
    NR = (*table).NRho-1,
    NT = (*table).NT-1;
  FILE* h;
  char name[STRSIZE];
  
  //
  sprintf( name,"%s.%s",name_in,SES_305_SUFFIX );
  printf( "\nWrite SESAME table format for ions (%s):\n",name );
  if ((h = fopen(name,"w")) == NULL) {
    printf("\nFE-ERROR in write_305_format ---> Error occured while opening file !!!\n");
    exit(0);
  }
  fprintf(h," %04d0305      %15.8le%15.8le%15.8le\n",
	  matnumber,rhosolid,double(NR+1),double(NT+1) );
  //
  // Rho and T vectors:
  //  
  count = 0;
  for(i=0;i<=NR;i++ ) {
    fprintf(h,"%15.8e", (*table).Rho[i]*cgs2ses_rho );
    if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }  
  for(j=0;j<=NT;j++ ) {
    fprintf(h,"%15.8le", (*table).T[j]*cgs2ses_t ); 
    if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  } 

  for(j=0;j<=NT;j++)      // pressure :
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Pi[i][j]*cgs2ses_p );
      if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }  
  
  for(j=0;j<=NT;j++)   // energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Ei[i][j]*cgs2ses_e );
      if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }  
  
  for(j=0;j<=NT;j++)  // free energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).Fi[i][j]*cgs2ses_e );
      if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    } 
  fclose(h);

  printf(" Table size (densities x temperatures): %d x %d\n Table boundaries (density, temperature):\n", NR+1, NT+1);
  printf("  (%e g/cm^3, %e eV) ...\n", (*table).Rho[0], (*table).T[0]);
  if(NR>1 && NT<2) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[1], (*table).T[0]);
  else if(NR<2 && NT>1) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[0], (*table).T[1]);
  else if(NR>1 && NT>1) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[1], (*table).T[1]);
  printf("  ... (%e g/cm^3, %e eV)\n", (*table).Rho[NR], (*table).T[NT]);  
  printf("Done.\n");
  
  return;   
}

//////////////////////////////////////////////////////////////////

void write_txt_format( char* name_in, Qtable* table )
{
  // SESAME 301 standard format
  // indices start at 0
  //
  // with Pressure, Energy, Free Energy
  //
  // SESAME units are
  //
  // Pressure in GPa
  // energy in MJ/kg
  // density Mg/m3
  // temperature in Kelvin

  int i,j,
    NR = (*table).NRho-1,
    NT = (*table).NT-1;
  FILE* h;
  char name[STRSIZE];
  //
  sprintf( name,"%s.data.txt",name_in );
  printf( "\nWrite text table format (%s):\n", name );
  if ((h = fopen(name,"w")) == NULL) {
    printf( "\nFE-ERROR in write_txt_format ---> Error occured while opening file !!!\n");
    exit(0);
  }

  for(j=0;j<=NT;j++)  {
    for(i=0;i<=NR;i++) {
      fprintf(h,"%d\t%d\t%15.8le\t%15.8le\t%15.8le\t%15.8le\t%15.8le\t%15.8le\t%15.8le\t%15.8le\n",
       i,
       j,
       (*table).Rho[i] *cgs2ses_rho,
       (*table).T[j] *cgs2ses_t,
       (*table).P[i][j] *cgs2ses_p,
       (*table).Pi[i][j] *cgs2ses_p,
       (*table).Pe[i][j] *cgs2ses_p,
       (*table).E[i][j] *cgs2ses_e,
       (*table).Ei[i][j] *cgs2ses_e ,
       (*table).Ee[i][j] *cgs2ses_e);
    }
    fprintf(h,"\n");  
  }
  
  fclose(h);

  printf(" Table size (densities x temperatures): %d x %d\n Table boundaries (density, temperature):\n", NR+1, NT+1);
  printf("  (%e g/cm^3, %e eV) ...\n", (*table).Rho[0], (*table).T[0]);
  if(NR>1 && NT<2) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[1], (*table).T[0]);
  else if(NR<2 && NT>1) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[0], (*table).T[1]);
  else if(NR>1 && NT>1) printf("  ... (%e g/cm^3, %e eV) ...\n", (*table).Rho[1], (*table).T[1]);
  printf("  ... (%e g/cm^3, %e eV)\n", (*table).Rho[NR], (*table).T[NT]);  
  printf("Done.\n");

  return;   
}

//////////////////////////////////////////////////////////////////

void write_Rostock_format(  char* name_in, Qtable* table)
{ 
  // write isotherms : charge state and pressure vs density
  
  FILE* h;
  int NR = (*table).NRho-1,
    NT = (*table).NT-1,
    i,j;
  char name[STRSIZE];
  sprintf( name, "%s.%s", name_in, ROSTOCK_SUFFIX );
  printf( "\nWrite charge state table / Rostock format (%s)...",name );
  h = fopen( name, "w" );
  for(j=0;j<=NT;j++) {
    fprintf( h, "Isotherme T = %.0f Kelvin \n", (*table).T[j]*eV2Kelvin );
    fprintf( h, "Moleküldichte[1/cm^3]  Massendichte[g/cm^3]  Druck[MBar]  Ladungszustand\n" );
    for(i=0;i<=NR;i++) {
      fprintf( h,"%e          %e          %e    %e\n", 
	       (*table).Rho[i]/((*table).Atot*M_proton), (*table).Rho[i],
	       (*table).P[i][j]*cgs2MBar, (*table).Qtot[i][j] );
    }
  }
  fclose( h);
  printf(" done.\n" );
  return;
}

//////////////////////////////////////////////////////////////////
// eof.