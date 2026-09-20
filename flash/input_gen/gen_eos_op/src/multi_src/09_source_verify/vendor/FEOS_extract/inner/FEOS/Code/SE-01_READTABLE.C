//////////////////////////////////////////////////////////////////
// service routines for reading EOS tables 
// used by the SHOWEOS table visualization tool
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#include "SE-01_READTABLE.H"

//////////////////////////////////////////////////////////////////

void read_FEOS_format( char* name_in, Qtable* qtab, Units* units )
{
  FILE* h;
  int i,j,k,NR,NT,Nelements;
  int fscanfresult __attribute__ ((unused));
  double d;
  char name[STRSIZE];
  
  sprintf(name,"%s.%s",name_in, "feos");
  printf("\nCheck file version and read table size from source %s...", name );
  if ((h=fopen(name,"r"))==NULL) {
    printf("\nSE-ERROR in read_FEOS_format ---> File %s not found !!!\n",name);
    exit(0);
  }

  // Check file version:
  fscanfresult = fscanf(h,"%le",&d );
  if(d>12.06) {
    printf("\nSE-ERROR in read_FEOS_format ---> %s (file version %4.2f) cannot be read by this (old) version of SHOWEOS !!!\n",name,d);
    exit(0);  
  }

  // Read table parameters:
  fscanfresult = fscanf(h,"%le",&d); (*qtab).NRho = int(d);
  fscanfresult = fscanf(h,"%le",&d); (*qtab).NT = int(d);
  fscanfresult = fscanf(h,"%le",&d); (*qtab).Nelements = int(d);
  NR = (*qtab).NRho-1;
  NT = (*qtab).NT-1;
  Nelements = (*qtab).Nelements-1;
  printf(" done.\n");   

  // Allocate memory:
  GetQTABmemory1(qtab);
  GetQTABmemory2(qtab, 1);

  printf("\nRead FEOS table format (%s):\n", name );

  // Read material parameters:
  fscanfresult = fscanf(h,"%le",&d); (*qtab).Tcalclimit = d;
  fscanfresult = fscanf(h,"%le",&d); (*qtab).Rhocalclimit = d;
  fscanfresult = fscanf(h,"%le",&d); (*qtab).RhoRef = d;   
  fscanfresult = fscanf(h,"%le",&d); (*qtab).TRef = d;
  fscanfresult = fscanf(h,"%le",&d); (*qtab).BulkModulusRef = d;
  fscanfresult = fscanf(h,"%le",&d); (*qtab).SESAMEnumber = int(d);
  fscanfresult = fscanf(h,"%le",&d); (*qtab).ElectronOffset = d;
  fscanfresult = fscanf(h,"%le",&d); (*qtab).IonOffset = d;
  fscanfresult = fscanf(h,"%le",&d); (*qtab).Ecoh = d;
  fscanfresult = fscanf(h,"%le",&d); (*qtab).softsphere_n = d;
  fscanfresult = fscanf(h,"%le",&d); (*qtab).softsphere_m = d;
  fscanfresult = fscanf(h,"%le",&d); (*qtab).softsphere_A = d;
  fscanfresult = fscanf(h,"%le",&d); (*qtab).softsphere_B = d;
  fscanfresult = fscanf(h,"%le",&d); (*qtab).Atot = d;
  fscanfresult = fscanf(h,"%le",&d); (*qtab).Ztot = d;
  fscanfresult = fscanf(h,"%le",&d); (*qtab).Xtot = d;
  for(k=0;k<=Nelements;k++ ) { fscanfresult = fscanf(h,"%le",&d); (*qtab).A[k] = d; }
  for(k=0;k<=Nelements;k++ ) { fscanfresult = fscanf(h,"%le",&d); (*qtab).Z[k] = d; }
  for(k=0;k<=Nelements;k++ ) { fscanfresult = fscanf(h,"%le",&d); (*qtab).X[k] = d; }  
                                                                                       
  // Read in densities and temperatures:
  for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).Rho[i] = d; }
  for(j=0;j<=NT;j++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).T[j] = d; }
   
  // Read in thermodynamic values:
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).P[i][j] = d; } 
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).E[i][j] = d; }
  for(j=0;j<=NT;j++) 
	  for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).S[i][j] = d; }
  for(j=0;j<=NT;j++) 
	  for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).F[i][j] = d; }
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).Pe[i][j] = d; } 
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).Ee[i][j] = d; }
  for(j=0;j<=NT;j++) 
	  for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).Se[i][j] = d; }
  for(j=0;j<=NT;j++) 
	  for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).Fe[i][j] = d; }
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).Pi[i][j] = d; } 
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).Ei[i][j] = d; }
  for(j=0;j<=NT;j++) 
	  for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).Si[i][j] = d; }
  for(j=0;j<=NT;j++) 
	  for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).Fi[i][j] = d; }
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).PTF[i][j] = d; } 
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).ETF[i][j] = d; }
  for(j=0;j<=NT;j++) 
	  for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).STF[i][j] = d; }
  for(j=0;j<=NT;j++) 
	  for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).FTF[i][j] = d; }
  for(j=0;j<=NT;j++) 
	  for(i=0;i<=NR;i++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).Qtot[i][j] = d; }
  for(j=0;j<=NT;j++) 
	  for(i=0;i<=NR;i++)
      for(k=0;k<=Nelements;k++) { fscanfresult = fscanf(h,"%le",&d); (*qtab).Q[k][i][j] = d; }

  fclose(h);
    
  printf(" Table size (densities x temperatures): %d x %d\n Table boundaries (Rho [%e g/cm^3], T [%e eV]):\n", NR+1, NT+1, (*units).R, (*units).T);
  printf("  (%e, %e) ...\n", (*qtab).Rho[0]/(*units).R, (*qtab).T[0]/(*units).T);
  if(NR>1 && NT<2) printf("  ... (%e, %e) ...\n", (*qtab).Rho[1]/(*units).R, (*qtab).T[0]/(*units).T);
  else if(NR<2 && NT>1) printf("  ... (%e, %e) ...\n", (*qtab).Rho[0]/(*units).R, (*qtab).T[1]/(*units).T);
  else if(NR>1 && NT>1) printf("  ... (%e, %e) ...\n", (*qtab).Rho[1]/(*units).R, (*qtab).T[1]/(*units).T);
  printf("  ... (%e, %e)\n", (*qtab).Rho[NR]/(*units).R, (*qtab).T[NT]/(*units).T);  
  printf("Done.\n");  

  return;
}

//////////////////////////////////////////////////////////////////

void read_301_format( char* name_in, Qtable* qtab, Units* units )
{
  FILE* h;
  int i,j,k,NR,NT,Nelements;
  int fscanfresult __attribute__ ((unused));
  double d,nr_in,nt_in;
  char name[STRSIZE], chr[STRSIZE];
  
  sprintf(name,"%s.%s",name_in, SES_301_SUFFIX);
  printf("\nRead table size from source %s...", name );
  if ((h=fopen(name,"r"))==NULL) {
    printf("\nSE-ERROR in read_301_format ---> File %s not found !!!\n",name);
    exit(0);
  }

  // Find first line. 301 table start-signal is 0301 (after Sesame-Number).
  do fscanfresult = fscanf(h,"%s", chr ); 
  while (strstr(chr, "0301")==NULL);
  strncpy(chr,chr,4);
  (*qtab).SESAMEnumber = atoi(chr);

  // Read table parameters:
  fscanfresult = fscanf(h,"%le%le%le",&d,&nr_in,&nt_in );
  (*qtab).RhoRef= d;
  (*qtab).NRho = int(nr_in);
  (*qtab).NT = int(nt_in);
  NR = (*qtab).NRho-1;
  NT = (*qtab).NT-1;
  (*qtab).Nelements = 1;
  Nelements = (*qtab).Nelements-1;
  printf(" done.\n");   

  // Allocate memory:
  GetQTABmemory1(qtab);
  GetQTABmemory2(qtab, 1);

  printf("\nRead SESAME table 301 format (%s):\n", name );

  // Reset material parameters which are not present in 301 table format:    
  (*qtab).TRef = (*qtab).BulkModulusRef = (*qtab).Atot = (*qtab).Ztot = (*qtab).Xtot =
  (*qtab).Ecoh = (*qtab).softsphere_n = (*qtab).softsphere_m = (*qtab).softsphere_A = (*qtab).softsphere_B =
  (*qtab).ElectronOffset = (*qtab).IonOffset = (*qtab).Tcalclimit = (*qtab).Rhocalclimit = 0.0;
  
  // Reset thermodynamic quantities which are not present in 301 table format:
  for(k=0;k<=Nelements;k++) 
    (*qtab).A[k] = (*qtab).Z[k] = (*qtab).X[k] = 0.0;  
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) {
      (*qtab).Pe[i][j] = (*qtab).Ee[i][j] = (*qtab).Se[i][j] = (*qtab).Fe[i][j] =
      (*qtab).Pi[i][j] = (*qtab).Ei[i][j] = (*qtab).Si[i][j] = (*qtab).Fi[i][j] =
      (*qtab).PTF[i][j] = (*qtab).ETF[i][j] = (*qtab).STF[i][j] = (*qtab).FTF[i][j] =
      (*qtab).S[i][j] = (*qtab).Qtot[i][j] = 0.0;
      for(k=0;k<=Nelements;k++) (*qtab).Q[k][i][j] = 0.0;
    }
  
  // Read in densities and temperatures:
  for(i=0;i<=NR;i++) { 
    fscanfresult = fscanf(h,"%le",&d);
    (*qtab).Rho[i] = d / cgs2ses_rho;
  }
  for(j=0;j<=NT;j++) { 
    fscanfresult = fscanf(h,"%le",&d); 
    (*qtab).T[j] = d / cgs2ses_t; 
  }
   
  // Read in thermodynamic values:
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) { 
      fscanfresult = fscanf(h,"%le",&d);
      (*qtab).P[i][j] = d / cgs2ses_p;
    } 
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) {
      fscanfresult = fscanf(h,"%le",&d);
      (*qtab).E[i][j] = d / cgs2ses_e;
    }
  for(j=0;j<=NT;j++) 
	  for(i=0;i<=NR;i++) { 
      fscanfresult = fscanf(h,"%le",&d);
      (*qtab).F[i][j] = d / cgs2ses_e;
      (*qtab).S[i][j] = ((*qtab).E[i][j]-(*qtab).F[i][j]) / (*qtab).T[j];
    }

  fclose(h);

  printf(" Table size (densities x temperatures): %d x %d\n Table boundaries (Rho [%e g/cm^3], T [%e eV]):\n", NR+1, NT+1, (*units).R, (*units).T);
  printf("  (%e, %e) ...\n", (*qtab).Rho[0]/(*units).R, (*qtab).T[0]/(*units).T);
  if(NR>1 && NT<2) printf("  ... (%e, %e) ...\n", (*qtab).Rho[1]/(*units).R, (*qtab).T[0]/(*units).T);
  else if(NR<2 && NT>1) printf("  ... (%e, %e) ...\n", (*qtab).Rho[0]/(*units).R, (*qtab).T[1]/(*units).T);
  else if(NR>1 && NT>1) printf("  ... (%e, %e) ...\n", (*qtab).Rho[1]/(*units).R, (*qtab).T[1]/(*units).T);
  printf("  ... (%e, %e)\n", (*qtab).Rho[NR]/(*units).R, (*qtab).T[NT]/(*units).T);  
  printf("Done.\n");

  return;
}

//////////////////////////////////////////////////////////////////

void read_304_format( char* name_in, Qtable* qtab, Units* units )
{
  FILE* h;
  int i,j,k,NR,NT,Nelements;
  int fscanfresult __attribute__ ((unused));
  double d,nr_in,nt_in;
  char name[STRSIZE], chr[STRSIZE];
  
  sprintf(name,"%s.%s",name_in, SES_304_SUFFIX);
  printf("\nRead table size from source %s...", name );
  if ((h=fopen(name,"r"))==NULL) {
    printf("\nSE-ERROR in read_304_format ---> File %s not found !!!\n",name);
    exit(0);
  }

  // Find first line. 304 table start-signal is 0301 (after Sesame-Number).
  do fscanfresult = fscanf(h,"%s", chr ); 
  while (strstr(chr, "0304")==NULL);
  strncpy(chr,chr,4);
  (*qtab).SESAMEnumber = atoi(chr);

  // Read table parameters:
  fscanfresult = fscanf(h,"%le%le%le",&d,&nr_in,&nt_in );
  (*qtab).RhoRef= d;
  (*qtab).NRho = int(nr_in);
  (*qtab).NT = int(nt_in);
  NR = (*qtab).NRho-1;
  NT = (*qtab).NT-1;
  (*qtab).Nelements = 1;
  Nelements = (*qtab).Nelements-1;
  printf(" done.\n");   

  // Allocate memory:
  GetQTABmemory1(qtab);
  GetQTABmemory2(qtab, 1);

  printf("\nRead SESAME table 304 format (%s):\n", name );

  // Reset material parameters which are not present in 301 table format:    
  (*qtab).TRef = (*qtab).BulkModulusRef = (*qtab).Atot = (*qtab).Ztot = (*qtab).Xtot =
  (*qtab).Ecoh = (*qtab).softsphere_n = (*qtab).softsphere_m = (*qtab).softsphere_A = (*qtab).softsphere_B =
  (*qtab).ElectronOffset = (*qtab).IonOffset = (*qtab).Tcalclimit = (*qtab).Rhocalclimit = 0.0;
  
  // Reset thermodynamic quantities which are not present in 304 table format:
  for(k=0;k<=Nelements;k++) 
    (*qtab).A[k] = (*qtab).Z[k] = (*qtab).X[k] = 0.0;  
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) {
      (*qtab).P[i][j] = (*qtab).E[i][j] = (*qtab).S[i][j] = (*qtab).F[i][j] =
      (*qtab).Pi[i][j] = (*qtab).Ei[i][j] = (*qtab).Si[i][j] = (*qtab).Fi[i][j] =
      (*qtab).PTF[i][j] = (*qtab).ETF[i][j] = (*qtab).STF[i][j] = (*qtab).FTF[i][j] =
      (*qtab).Se[i][j] = (*qtab).Qtot[i][j] = 0.0;
      for(k=0;k<=Nelements;k++) (*qtab).Q[k][i][j] = 0.0;
    }
  
  // Read in densities and temperatures:
  for(i=0;i<=NR;i++) { 
    fscanfresult = fscanf(h,"%le",&d);
    (*qtab).Rho[i] = d / cgs2ses_rho;
  }
  for(j=0;j<=NT;j++) { 
    fscanfresult = fscanf(h,"%le",&d); 
    (*qtab).T[j] = d / cgs2ses_t; 
  }
   
  // Read in thermodynamic values:
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) { 
      fscanfresult = fscanf(h,"%le",&d);
      (*qtab).Pe[i][j] = d / cgs2ses_p;
    } 
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) {
      fscanfresult = fscanf(h,"%le",&d);
      (*qtab).Ee[i][j] = d / cgs2ses_e;
    }
  for(j=0;j<=NT;j++) 
	  for(i=0;i<=NR;i++) { 
      fscanfresult = fscanf(h,"%le",&d);
      (*qtab).Fe[i][j] = d / cgs2ses_e;
      (*qtab).Se[i][j] = ((*qtab).Ee[i][j]-(*qtab).Fe[i][j]) / (*qtab).T[j];
    }

  fclose(h);
    
  printf(" Table size (densities x temperatures): %d x %d\n Table boundaries (Rho [%e g/cm^3], T [%e eV]):\n", NR+1, NT+1, (*units).R, (*units).T);
  printf("  (%e, %e) ...\n", (*qtab).Rho[0]/(*units).R, (*qtab).T[0]/(*units).T);
  if(NR>1 && NT<2) printf("  ... (%e, %e) ...\n", (*qtab).Rho[1]/(*units).R, (*qtab).T[0]/(*units).T);
  else if(NR<2 && NT>1) printf("  ... (%e, %e) ...\n", (*qtab).Rho[0]/(*units).R, (*qtab).T[1]/(*units).T);
  else if(NR>1 && NT>1) printf("  ... (%e, %e) ...\n", (*qtab).Rho[1]/(*units).R, (*qtab).T[1]/(*units).T);
  printf("  ... (%e, %e)\n", (*qtab).Rho[NR]/(*units).R, (*qtab).T[NT]/(*units).T);  
  printf("Done.\n"); 

  return;
}

//////////////////////////////////////////////////////////////////

void read_305_format( char* name_in, Qtable* qtab, Units* units )
{
  FILE* h;
  int i,j,k,NR,NT,Nelements;
  int fscanfresult __attribute__ ((unused));
  double d,nr_in,nt_in;
  char name[STRSIZE], chr[STRSIZE];
  
  sprintf(name,"%s.%s",name_in, SES_305_SUFFIX);
  printf("\nRead table size from source %s...", name );
  if ((h=fopen(name,"r"))==NULL) {
    printf("\nSE-ERROR in read_305_format ---> File %s not found !!!\n",name);
    exit(0);
  }

  // Find first line. 305 table start-signal is 0301 (after Sesame-Number).
  do fscanfresult = fscanf(h,"%s", chr ); 
  while (strstr(chr, "0305")==NULL);
  strncpy(chr,chr,4);
  (*qtab).SESAMEnumber = atoi(chr);

  // Read table parameters:
  fscanfresult = fscanf(h,"%le%le%le",&d,&nr_in,&nt_in );
  (*qtab).RhoRef= d;
  (*qtab).NRho = int(nr_in);
  (*qtab).NT = int(nt_in);
  NR = (*qtab).NRho-1;
  NT = (*qtab).NT-1;
  (*qtab).Nelements = 1;
  Nelements = (*qtab).Nelements-1;
  printf(" done.\n");   

  // Allocate memory:
  GetQTABmemory1(qtab);
  GetQTABmemory2(qtab, 1);

  printf("\nRead SESAME table 305 format (%s):\n", name );

  // Reset material parameters which are not present in 301 table format:    
  (*qtab).TRef = (*qtab).BulkModulusRef = (*qtab).Atot = (*qtab).Ztot = (*qtab).Xtot =
  (*qtab).Ecoh = (*qtab).softsphere_n = (*qtab).softsphere_m = (*qtab).softsphere_A = (*qtab).softsphere_B =
  (*qtab).ElectronOffset = (*qtab).IonOffset = (*qtab).Tcalclimit = (*qtab).Rhocalclimit = 0.0;
  
  // Reset thermodynamic quantities which are not present in 305 table format:
  for(k=0;k<=Nelements;k++) 
    (*qtab).A[k] = (*qtab).Z[k] = (*qtab).X[k] = 0.0;  
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) {
      (*qtab).Pe[i][j] = (*qtab).Ee[i][j] = (*qtab).Se[i][j] = (*qtab).Fe[i][j] =
      (*qtab).P[i][j] = (*qtab).E[i][j] = (*qtab).S[i][j] = (*qtab).F[i][j] =
      (*qtab).PTF[i][j] = (*qtab).ETF[i][j] = (*qtab).STF[i][j] = (*qtab).FTF[i][j] =
      (*qtab).Si[i][j] = (*qtab).Qtot[i][j] = 0.0;
      for(k=0;k<=Nelements;k++) (*qtab).Q[k][i][j] = 0.0;
    }
  
  // Read in densities and temperatures:
  for(i=0;i<=NR;i++) { 
    fscanfresult = fscanf(h,"%le",&d);
    (*qtab).Rho[i] = d / cgs2ses_rho;
  }
  for(j=0;j<=NT;j++) { 
    fscanfresult = fscanf(h,"%le",&d); 
    (*qtab).T[j] = d / cgs2ses_t; 
  }
   
  // Read in thermodynamic values:
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) { 
      fscanfresult = fscanf(h,"%le",&d);
      (*qtab).Pi[i][j] = d / cgs2ses_p;
    } 
  for(j=0;j<=NT;j++) 
    for(i=0;i<=NR;i++) {
      fscanfresult = fscanf(h,"%le",&d);
      (*qtab).Ei[i][j] = d / cgs2ses_e;
    }
  for(j=0;j<=NT;j++) 
	  for(i=0;i<=NR;i++) { 
      fscanfresult = fscanf(h,"%le",&d);
      (*qtab).Fi[i][j] = d / cgs2ses_e;
      (*qtab).Si[i][j] = ((*qtab).Ei[i][j]-(*qtab).Fi[i][j]) / (*qtab).T[j];
    }

  fclose(h);
    
  printf(" Table size (densities x temperatures): %d x %d\n Table boundaries (Rho [%e g/cm^3], T [%e eV]):\n", NR+1, NT+1, (*units).R, (*units).T);
  printf("  (%e, %e) ...\n", (*qtab).Rho[0]/(*units).R, (*qtab).T[0]/(*units).T);
  if(NR>1 && NT<2) printf("  ... (%e, %e) ...\n", (*qtab).Rho[1]/(*units).R, (*qtab).T[0]/(*units).T);
  else if(NR<2 && NT>1) printf("  ... (%e, %e) ...\n", (*qtab).Rho[0]/(*units).R, (*qtab).T[1]/(*units).T);
  else if(NR>1 && NT>1) printf("  ... (%e, %e) ...\n", (*qtab).Rho[1]/(*units).R, (*qtab).T[1]/(*units).T);
  printf("  ... (%e, %e)\n", (*qtab).Rho[NR]/(*units).R, (*qtab).T[NT]/(*units).T);  
  printf("Done.\n"); 

  return;
}

//////////////////////////////////////////////////////////////////
// eof.