//////////////////////////////////////////////////////////////////
// service routines for isotherms, isochores, hugoniots, etc. 
// used by the SHOWEOS table visualization tool
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#include "SE-03_SERVICES.H"

//////////////////////////////////////////////////////////////////

int Check_Density( Qtable* qtab, double r, double unit )
{
  if(r < (*qtab).Rho[0] || r > (*qtab).Rho[(*qtab).NRho-1]) {
   	printf("\nRho = %e [%e g/cm^3] beyond table boundaries !!!\n", r/unit, unit );
	  return 0;
	}	  
  return 1;
}

//////////////////////////////////////////////////////////////////

int Check_Temperature( Qtable* qtab, double t, double unit )
{
  if(t < (*qtab).T[0] || t > (*qtab).T[(*qtab).NT-1]) {
   	printf("\nT = %e [%e eV] beyond table boundaries !!!\n", t/unit, unit );
	  return 0;
	}	  
  return 1;
}

//////////////////////////////////////////////////////////////////

int Check_Quantity( Qtable* qtab, int qn, int filetype, int element )
{
  if(qn<1 || qn>8) {
   	printf("\nInvalid choice for quantity: %d !!!\n", qn );
	  return 0;  
  }
  if(qn==8 && filetype == 2) {
   	printf("\nCharge state data not available for SESAME EOS !!!\n" );
	  return 0;  
  }
  if(qn==8 && (element < 0 || element > (*qtab).Nelements)) {
   	printf("\nInvalid element number: %d !!!\n", element );
	  return 0;
	}	  
  return 1;
}

//////////////////////////////////////////////////////////////////

void GetPointArray( double* ArrayIn, int ArrayInSize, double* ArrayOut, int* ArrayOutSize,
		                int OriginalFlag, int ColdFlag, int LogFlag, double Xmin, double Xmax )
{  
  int i, c=0;
  double x, px, mx;
 
  if( OriginalFlag )
  {
    if( ColdFlag && ArrayIn[0]<Xmin ) { ArrayOut[0] = ArrayIn[0]; c++; }
    for( i = 0; i<= ArrayInSize; i++ )
    {
	    if( (ArrayIn[i] >= Xmin) && (ArrayIn[i] <= Xmax) )
	    {
	      ArrayOut[c] = ArrayIn[i];
	      c++;
	    }
	  }
    *ArrayOutSize = c;
    return;
  } 
  else
  {
    if( LogFlag ) // logarithmic scaling:
    {
	    if( ColdFlag && ArrayIn[0]<Xmin ) { ColdFlag = 1; ArrayOut[0] = ArrayIn[0]; c++; }
	    else ColdFlag = 0;
	    x = Xmin;
	    mx = (*ArrayOutSize-ColdFlag-1) ? pow( (Xmax/Xmin), 1.0 / ( (*ArrayOutSize)-1-ColdFlag ) ) : 0.0;
	    for( i = 1; i<= (*ArrayOutSize) -ColdFlag; i++ )
	    {
	      ArrayOut[c] = x;
	      x *= mx;
	      c++;
	    }
      return;
    }
    else // linear scaling:
    {
	    if( ColdFlag && ArrayIn[0]<Xmin ) { ColdFlag = 1; ArrayOut[0] = ArrayIn[0]; c++; }
	    else ColdFlag = 0;
	    x = Xmin;
	    px = (*ArrayOutSize-1-ColdFlag) ? (Xmax-Xmin)/(*ArrayOutSize-1-ColdFlag) : 0.0;
	    for( i = 1; i <= *ArrayOutSize -ColdFlag; i++ )
	    {
	      ArrayOut[c] = x;
	      x += px;
	      c++;
	    }
	    return;
    }
  }
  
  return;
}

//////////////////////////////////////////////////////////////////

void GetQuantityName( char* name, int qn, int element, int eostype )
{
  switch( qn ) {
  case 1 : sprintf(name,"%s", DENSITY_SUFFIX); break;
  case 2 : sprintf(name,"%s", VOLUME_SUFFIX); break;
  case 3 : sprintf(name,"%s", TEMPERATURE_SUFFIX); break;
  case 4 : sprintf(name,"%s", PRESSURE_SUFFIX); break;
  case 5 : sprintf(name,"%s", ENERGY_SUFFIX); break;
  case 6 : sprintf(name,"%s", FREE_ENERGY_SUFFIX); break;
  case 7 : sprintf(name,"%s", ENTROPY_SUFFIX); break;
  case 8 : sprintf(name,"%s", CHARGE_SUFFIX); break;
  case 9 : sprintf(name,"%s%s", VELOCITY_SUFFIX, "s"); break;
  case 10 : sprintf(name,"%s%s", VELOCITY_SUFFIX, "p"); break;
  default : { printf( "\nSE-ERROR in GetQuantityName ---> Invalid quantity input !!!\n" ); exit(0); }
  }
  
  if(qn>3 && qn!=8) {
    switch( eostype ) {
    case 2 : sprintf(name,"%s%s", name, ELECTRON_SUFFIX); break;
    case 3 : sprintf(name,"%s%s", name, ION_SUFFIX); break;
    case 4 : sprintf(name,"%s%s", name, TF_SUFFIX); break;
    default : break;     
    }
  }
  else if(qn==8 && element) sprintf(name,"%s[%d]", name, element);
  else if(qn==8 && !element) sprintf(name,"%stot", name);
  
  return;
}

//////////////////////////////////////////////////////////////////

double GetQuantity( int qn, Qtable* qtab, double r, double t, int element, int eostype, Units* units )
{
  double** PQ = NULL;

  if(!Check_Density(qtab, r, (*units).R)) exit(0);
  if(!Check_Temperature(qtab, t, (*units).T)) exit(0);

  if(qn<4 || qn>7) {
    switch( qn ) {
    case 1 : return r;
    case 2 : return 1.0/r;
    case 3 : return t;
    case 8 : { if(element>0&&element<=(*qtab).Nelements) {PQ = (*qtab).Q[element-1];} else {PQ = (*qtab).Qtot;} break; }
    default : { printf( "\nSE-ERROR in GetQuantity ---> Invalid quantity input !!!\n" ); exit(0); }
    }
  }
  else if(qn==4) {
    switch( eostype ) {  
    case 2 : PQ = (*qtab).Pe; break;
    case 3 : PQ = (*qtab).Pi; break;
    case 4 : PQ = (*qtab).PTF; break;
    default : PQ = (*qtab).P; break;
    }  
  }
  else if(qn==5) {
    switch( eostype ) {  
    case 2 : PQ = (*qtab).Ee; break;
    case 3 : PQ = (*qtab).Ei; break;
    case 4 : PQ = (*qtab).ETF; break;
    default : PQ = (*qtab).E; break;
    }  
  }
  else if(qn==6) {
    switch( eostype ) {  
    case 2 : PQ = (*qtab).Fe; break;
    case 3 : PQ = (*qtab).Fi; break;
    case 4 : PQ = (*qtab).FTF; break;
    default : PQ = (*qtab).F; break;
    }  
  }
  else if(qn==7) {
    switch( eostype ) {  
    case 2 : PQ = (*qtab).Se; break;
    case 3 : PQ = (*qtab).Si; break;
    case 4 : PQ = (*qtab).STF; break;
    default : PQ = (*qtab).S; break;
    }  
  }
 
  return get_PQ_LI( (*qtab).Rho, (*qtab).T, r, t, PQ, (*qtab).NRho-1, (*qtab).NT-1 );
}

//////////////////////////////////////////////////////////////////

void GetUnitsName( char* name, int qn, int element, Units* units )
{
  switch( qn ) {
  case 1 : sprintf(name,"[%e %s]", GetUnits( qn, units ), "g/cm^3"); break;
  case 2 : sprintf(name,"[%e %s]", GetUnits( qn, units ), "cm^3/g"); break;
  case 3 : sprintf(name,"[%e %s]", GetUnits( qn, units ), "eV"); break;
  case 4 : sprintf(name,"[%e %s]", GetUnits( qn, units ), "dyne/cm^2"); break;
  case 5 : sprintf(name,"[%e %s]", GetUnits( qn, units ), "erg/g"); break;
  case 6 : sprintf(name,"[%e %s]", GetUnits( qn, units ), "erg/g"); break;
  case 7 : sprintf(name,"[%e %s]", GetUnits( qn, units ), "erg/(g*eV)"); break;
  case 8 : { if(element) {sprintf(name,"[per atom]");} else {sprintf(name,"[per molecule]");}  break; }
  case 9 : sprintf(name,"[%e %s]", GetUnits( qn, units ), "cm/s"); break;
  case 10 : sprintf(name,"[%e %s]", GetUnits( qn, units ), "cm/s"); break;
  default : { printf( "\nSE-ERROR in GetUnitsName ---> Invalid quantity input !!!\n" ); exit(0); }
  }

  return;
}

//////////////////////////////////////////////////////////////////

double GetUnits( int qn, Units* units )
{
  switch( qn ) {
  case 1 : return (*units).R;
  case 2 : return (*units).V;
  case 3 : return (*units).T;
  case 4 : return (*units).P;
  case 5 : return (*units).E;
  case 6 : return (*units).F;
  case 7 : return (*units).S;
  case 8 : return (*units).Q;
  case 9 : return (*units).U;
  case 10 : return (*units).U;
  default : { printf( "\nSE-ERROR in GetUnits ---> Invalid quantity input !!!\n" ); exit(0); }
  }
  
  return 0.0;
}

//////////////////////////////////////////////////////////////////

void GetMeshParameters( Qtable* qtab, char* file, Units* units, int first, 
                        int* Rarraysize, int* Tarraysize, int* Rnumber, int* Tnumber,
                        int* Roriginal, int* Rfirst, int* Rlog, double* Rmin, double* Rmax,
                        int* Toriginal, int* Tfirst, int* Tlog, double* Tmin, double* Tmax )
{
  readfile rf;
  char name[STRSIZE];
  int NR=(*qtab).NRho-1, NT=(*qtab).NT-1;
  double Runit=(*units).R, Tunit=(*units).T;

  sprintf(name,"%s.%s", file, PARFILE_SUFFIX);           
  rf.openinput(name); 
  *Tmin = atof( rf.setget( (char*)"Rho-T-Mesh",(char*)"Tmin") ) * Tunit;
  if(!Check_Temperature(qtab, *Tmin, Tunit)) exit(0); 
  *Tmax = atof( rf.setget( (char*)"Rho-T-Mesh",(char*)"Tmax") ) * Tunit;
  if(!Check_Temperature(qtab, *Tmax, Tunit)) exit(0);
  if(*Tmin>*Tmax) {printf("\nTmin > Tmax !!!\n"); exit(0);}
  if(first) *Tfirst = atoi( rf.setget( (char*)"Rho-T-Mesh", (char*)"Tfirst") );
  else *Tfirst = 0;
  *Toriginal = atoi( rf.setget( (char*)"Rho-T-Mesh", (char*)"Toriginal" ) );
  *Tnumber = atoi( rf.setget( (char*)"Rho-T-Mesh", (char*)"Tnumber") );
  if(!(*Toriginal) && *Tnumber+*Tfirst<1) {printf("\nTnumber < %d !!!\n", 1-*Tfirst); exit(0);}
  *Tlog = atoi( rf.setget( (char*)"Rho-T-Mesh", (char*)"Tlog" ) );
  *Rmin = atof( rf.setget( (char*)"Rho-T-Mesh",(char*)"Rhomin") ) * Runit;
  if(!Check_Density(qtab, *Rmin, Runit)) exit(0);  
  *Rmax = atof( rf.setget( (char*)"Rho-T-Mesh",(char*)"Rhomax") ) * Runit;
  if(!Check_Density(qtab, *Rmax, Runit)) exit(0);
  if(*Rmin>*Rmax) {printf("\nRhomin > Rhomax !!!\n"); exit(0);}
  if(first) *Rfirst = atoi( rf.setget( (char*)"Rho-T-Mesh", (char*)"Rhofirst") );
  else *Rfirst = 0;
  *Roriginal = atoi( rf.setget( (char*)"Rho-T-Mesh", (char*)"Rhooriginal" ) );
  *Rnumber = atoi( rf.setget( (char*)"Rho-T-Mesh", (char*)"Rhonumber") );
  if(!(*Roriginal) && *Rnumber+*Rfirst<1) {printf("\nRhonumber < %d !!!\n", 1-*Rfirst); exit(0);}
  *Rlog = atoi( rf.setget( (char*)"Rho-T-Mesh", (char*)"Rholog" ) );
  rf.closeinput();
  if(*Toriginal) *Tarraysize=NT+1;
  else *Tarraysize=*Tnumber+1;
  if(*Roriginal) *Rarraysize=NR+1;
  else *Rarraysize=*Rnumber+1;
    
  return;
}

//////////////////////////////////////////////////////////////////

void GetOutputQuantity( Qtable* qtab, char* file, Units* units, int fileformat, int eostype,
                        char* category, char* variable1, char* variable2, int* Qquantity, 
                        double* Qunit, int* Qelement, char* Qunitname, char* Qname )
{
  readfile rf;
  char name[STRSIZE];

  // Read and determine output quantities and units:
  sprintf(name,"%s.%s", file, PARFILE_SUFFIX);
  rf.openinput(name);
  *Qquantity = atoi( rf.setget( category,variable1 ) );        
  if(*Qquantity==8) *Qelement = atoi( rf.setget( category,variable2 ) );
  else *Qelement = 0;
  if(!Check_Quantity( qtab, *Qquantity, fileformat, *Qelement )) exit(0);
  *Qunit = GetUnits( *Qquantity, units );
  GetUnitsName( Qunitname, *Qquantity, *Qelement, units );
  GetQuantityName( Qname, *Qquantity, *Qelement, eostype );
  rf.closeinput();
  
  return;
}

//////////////////////////////////////////////////////////////////

void Isotherms( Qtable* qtab, char* file, Units* units, int fileformat, int eostype )
{ 
  FILE* h;
  readfile rf;
  char name[STRSIZE], suffix[STRSIZE], Xname[STRSIZE], Yname[STRSIZE], 
       Xunitname[STRSIZE], Yunitname[STRSIZE];
  int i, l, Tnumber, Rnumber, Rarraysize, Tarraysize, NR=(*qtab).NRho-1, NT=(*qtab).NT-1,
      Xquantity, Xelement, Yquantity, Yelement, 
      Tfirst, Toriginal, Tlog, Rfirst, Roriginal, Rlog;
  double R, T, Tmin, Tmax, Rmin, Rmax, Tunit=(*units).T, Xunit, Yunit,
         *temperatures, *densities;

  printf( "\nCalculate isotherms:\n" );

  // Get density-temperature mesh parameters:
  sprintf(name,"%s.%s", file, PARFILE_SUFFIX);
  printf(" Read and check mesh parameters from source %s...", name);  
  GetMeshParameters( qtab, file, units, 1, &Rarraysize, &Tarraysize, &Rnumber, &Tnumber,
                     &Roriginal, &Rfirst, &Rlog, &Rmin, &Rmax,
                     &Toriginal, &Tfirst, &Tlog, &Tmin, &Tmax );
  printf(" done.\n");

  // Initialize density-temperature mesh:
  printf(" Initialize density-temperature mesh...");
  temperatures=dvector( 0, Tarraysize );    
  GetPointArray( (*qtab).T, NT, temperatures, &Tnumber, Toriginal, Tfirst, Tlog, Tmin, Tmax );
  densities=dvector( 0, Rarraysize ); 
  GetPointArray( (*qtab).Rho, NR, densities, &Rnumber, Roriginal, Rfirst, Rlog, Rmin, Rmax );
  printf(" done.\n");

  // Read and determine output quantities and units:
  printf(" Determine output-quantities from source %s...", name);
  GetOutputQuantity( qtab, file, units, fileformat, eostype, 
                     (char*)"Isocurves", (char*)"Xquantity", (char*)"Xelement",
                     &Xquantity, &Xunit, &Xelement, Xunitname, Xname );
  GetOutputQuantity( qtab, file, units, fileformat, eostype, 
                     (char*)"Isocurves", (char*)"Yquantity", (char*)"Yelement",
                     &Yquantity, &Yunit, &Yelement, Yunitname, Yname );
  printf(" done.\n");

  // Calculate and write isotherms:
  sprintf(suffix,"%s-%s", Xname, Yname);
  sprintf(name,"%s.%s.%s", file, suffix, ISOTHERM_SUFFIX);
  h = fopen(name,"w");
  printf(" Processing temperature [%e eV]:\n ", Tunit);
  for( l = 0; l<= Tnumber-1; l++ )
  {
    T = temperatures[l];
    printf(" %e", T/Tunit);
    fflush( stdout );   
    fprintf( h, "# T = %e [%e eV]:\n", T/Tunit, Tunit );
    fprintf( h, "# %s %s  %s %s\n", Xname, Xunitname, Yname, Yunitname );
    for ( i = 0; i <= Rnumber-1; i++ ) 
    {
	    R = densities[i];
      fprintf(h,"%e  %e\n", (GetQuantity( Xquantity, qtab, R, T, Xelement, eostype, units )) / Xunit,
                            (GetQuantity( Yquantity, qtab, R, T, Yelement, eostype, units )) / Yunit );
    }
    if(l<(Tnumber-1)) fprintf(h, "&\n" );
    if(l==(Tnumber-1)) printf(".\n");
    else if((l+1)%5) printf(",");
    else printf(",\n ");
  }
  fprintf( h, "# eof." );
  fclose(h);
  
  // Free memory and print final output to console: 
  free_dvector( temperatures,0,Tarraysize );   
  free_dvector( densities,0,Rarraysize );
  printf(" Wrote %d isotherms to file %s.\nDone.\n", Tnumber, name); 
  	
  return;
}

//////////////////////////////////////////////////////////////////

void Isochores( Qtable* qtab, char* file, Units* units, int fileformat, int eostype )
{ 
  FILE* h;
  readfile rf;
  char name[STRSIZE], suffix[STRSIZE], Xname[STRSIZE], Yname[STRSIZE], 
       Xunitname[STRSIZE], Yunitname[STRSIZE];
  int i, l, Tnumber, Rnumber, Rarraysize, Tarraysize, NR=(*qtab).NRho-1, NT=(*qtab).NT-1, 
      Xquantity, Xelement, Yquantity, Yelement, 
      Tfirst, Toriginal, Tlog, Rfirst, Roriginal, Rlog;
  double R, T, Tmin, Tmax, Rmin, Rmax, Runit=(*units).R, Xunit, Yunit,
         *temperatures, *densities;

  printf( "\nCalculate isochores:\n" );

  // Get density-temperature mesh parameters:
  sprintf(name,"%s.%s", file, PARFILE_SUFFIX);
  printf(" Read and check mesh parameters from source %s...", name);  
  GetMeshParameters( qtab, file, units, 1, &Rarraysize, &Tarraysize, &Rnumber, &Tnumber,
                     &Roriginal, &Rfirst, &Rlog, &Rmin, &Rmax,
                     &Toriginal, &Tfirst, &Tlog, &Tmin, &Tmax );
  printf(" done.\n");

  // Initialize density-temperature mesh:
  printf(" Initialize density-temperature mesh...");
  temperatures=dvector( 0, Tarraysize );    
  GetPointArray( (*qtab).T, NT, temperatures, &Tnumber, Toriginal, Tfirst, Tlog, Tmin, Tmax );
  densities=dvector( 0, Rarraysize ); 
  GetPointArray( (*qtab).Rho, NR, densities, &Rnumber, Roriginal, Rfirst, Rlog, Rmin, Rmax );
  printf(" done.\n");

  // Read and determine output quantities and units:
  printf(" Determine output-quantities from source %s...", name);
  GetOutputQuantity( qtab, file, units, fileformat, eostype, 
                     (char*)"Isocurves", (char*)"Xquantity", (char*)"Xelement",
                     &Xquantity, &Xunit, &Xelement, Xunitname, Xname );
  GetOutputQuantity( qtab, file, units, fileformat, eostype, 
                     (char*)"Isocurves", (char*)"Yquantity", (char*)"Yelement",
                     &Yquantity, &Yunit, &Yelement, Yunitname, Yname );
  printf(" done.\n");

  // Calculate and write isochores:
  sprintf(suffix,"%s-%s", Xname, Yname);
  sprintf(name,"%s.%s.%s", file, suffix, ISOCHORE_SUFFIX);
  h = fopen(name,"w");
  printf(" Processing density [%e g/cm^3]:\n ", Runit);
  for( l = 0; l<= Rnumber-1; l++ )
  {
    R = densities[l];
    printf(" %e", R/Runit);
    fflush( stdout );   
    fprintf( h, "# Rho = %e [%e g/cm^3]:\n", R/Runit, Runit );
    fprintf( h, "# %s %s  %s %s\n", Xname, Xunitname, Yname, Yunitname );
    for ( i = 0; i <= Tnumber-1; i++ ) 
    {
	    T = temperatures[i];
      fprintf(h,"%e  %e\n", (GetQuantity( Xquantity, qtab, R, T, Xelement, eostype, units )) / Xunit,
                            (GetQuantity( Yquantity, qtab, R, T, Yelement, eostype, units )) / Yunit );
    }
    if(l<(Rnumber-1)) fprintf(h, "&\n" );
    if(l==(Rnumber-1)) printf(".\n");
    else if((l+1)%5) printf(",");
    else printf(",\n ");
  }
  fprintf( h, "# eof." );
  fclose(h);
 
  // Free memory and print final output to console: 
  free_dvector( temperatures,0,Tarraysize );   
  free_dvector( densities,0,Rarraysize );
  printf(" Wrote %d isochores to file %s.\nDone.\n", Rnumber, name); 
  	
  return;
}
  
//////////////////////////////////////////////////////////////////

void Isentropes( Qtable* qtab, char* file, Units* units, int fileformat, int eostype )
{ 
  FILE* h;
  readfile rf;
  char name[STRSIZE], suffix[STRSIZE], Xname[STRSIZE], Yname[STRSIZE], 
       Xunitname[STRSIZE], Yunitname[STRSIZE];
  int i, l, tc, tb, ts, del, Tnumber, Rnumber, NR=(*qtab).NRho-1, NT=(*qtab).NT-1, 
      Rarraysize, Tarraysize, Xquantity, Xelement, Yquantity, Yelement, 
      Tfirst, Toriginal, Tlog, Rfirst, Roriginal, Rlog;
  double S, dev, d1, d2, T, R, Tmin, Tmax, Rmin, Rmax, Tunit=(*units).T, Sunit=(*units).S,     
         Xunit, Yunit, *temperatures, *densities;
  bool stop, fulldens;

  printf( "\nCalculate isentropes:\n" );

  // Get density-temperature mesh parameters:
  sprintf(name,"%s.%s", file, PARFILE_SUFFIX);
  printf(" Read and check mesh parameters from source %s...", name);  
  GetMeshParameters( qtab, file, units, 0, &Rarraysize, &Tarraysize, &Rnumber, &Tnumber,
                     &Roriginal, &Rfirst, &Rlog, &Rmin, &Rmax,
                     &Toriginal, &Tfirst, &Tlog, &Tmin, &Tmax );
  printf(" done.\n");

  // Initialize density-temperature mesh:
  printf(" Initialize density-temperature mesh...");
  temperatures=dvector( 0, Tarraysize );    
  GetPointArray( (*qtab).T, NT, temperatures, &Tnumber, Toriginal, Tfirst, Tlog, Tmin, Tmax );
  densities=dvector( 0, Rarraysize ); 
  GetPointArray( (*qtab).Rho, NR, densities, &Rnumber, Roriginal, Rfirst, Rlog, Rmin, Rmax );
  printf(" done.\n");

  // Read and determine output quantities and units:
  printf(" Determine output-quantities from source %s...", name);
  GetOutputQuantity( qtab, file, units, fileformat, eostype, 
                     (char*)"Isocurves", (char*)"Xquantity", (char*)"Xelement",
                     &Xquantity, &Xunit, &Xelement, Xunitname, Xname );
  GetOutputQuantity( qtab, file, units, fileformat, eostype, 
                     (char*)"Isocurves", (char*)"Yquantity", (char*)"Yelement",
                     &Yquantity, &Yunit, &Yelement, Yunitname, Yname );
  printf(" done.\n");

  // Calculate and write isentropes:
  sprintf(suffix,"%s-%s", Xname, Yname);
  sprintf(name,"%s.%s.%s", file, suffix, ISENTROPE_SUFFIX);
  h = fopen(name,"w");  
  printf(" Processing entropy [%e erg/(g*eV)]:\n ", Sunit);
  fulldens = true;
  for( l = 0; l<= Tnumber-1; l++ )
  {
    T = temperatures[l];
    R = densities[0];
    S = GetQuantity( 7, qtab, R, T, 0, eostype, units );
    printf(" %e", S/Sunit);
    fflush( stdout );   
    fprintf( h, "# S = %e [%e erg/(g*eV)]:\n", S/Sunit, Sunit );
    fprintf( h, "# %s %s  %s %s\n", Xname, Xunitname, Yname, Yunitname );
    fprintf(h,"%e  %e\n", (GetQuantity( Xquantity, qtab, R, T, Xelement, eostype, units )) / Xunit,
                          (GetQuantity( Yquantity, qtab, R, T, Yelement, eostype, units )) / Yunit );
    tc = fetch( (*qtab).T, NT, T, &dev ) + 1;
    if(tc<1) tc = 1;
    if(tc>NT) tc = NT;
    stop = false;
    for( i = 1; i<= Rnumber-1; i++) 
    {
      R = densities[i];
      ts = tb = tc;
      if( (GetQuantity( 7, qtab, R, (*qtab).T[tc], 0, eostype, units )) > (GetQuantity( 7, qtab, R, (*qtab).T[tc-1], 0, eostype, units )) ) del = 1; else del = -1;
      while( (d1=S-(GetQuantity( 7, qtab, R, (*qtab).T[ts], 0, eostype, units ))) < 0.0)
      { 
        if(ts-del>=0 && ts-del<=NT) ts=ts-del;
        else { stop = true; fulldens = false; break; }
      }
      while( (d2=S-(GetQuantity( 7, qtab, R, (*qtab).T[tb], 0, eostype, units ))) > 0.0) 
      { 
        if(tb+del>=0 && tb+del<=NT) tb=tb+del;
        else { stop = true; fulldens = false; break; }
      }      
      if(!stop) 
      {
        tc = tb;
        T = (*qtab).T[ts] + ((*qtab).T[tb]-(*qtab).T[ts] ) * d1/(d1-d2);
        if(!Check_Temperature(qtab, T, Tunit)) exit(0); 
        fprintf(h,"%e  %e\n", (GetQuantity( Xquantity, qtab, R, T, Xelement, eostype, units )) / Xunit,
                              (GetQuantity( Yquantity, qtab, R, T, Yelement, eostype, units )) / Yunit );
      }                             
    }    
    if(l<(Tnumber-1)) fprintf(h, "&\n" );
    if(l==(Tnumber-1)) printf(".\n");
    else if((l+1)%5) printf(",");
    else printf(",\n ");
  }
  fprintf( h, "# eof." );
  fclose(h);

  // Free memory and print final output to console: 
  free_dvector( temperatures,0,Tarraysize );   
  free_dvector( densities,0,Rarraysize );
  printf(" Wrote %d isentropes to file %s.\n", Tnumber, name);
  if(!fulldens) printf(" Attention: Not all isentropes could be calculated up to Rhomax!\n");
  printf("Done.\n"); 
  
  return;
}

//////////////////////////////////////////////////////////////////

void Mountain( Qtable* qtab, char* file, Units* units, int fileformat, int eostype )
{
  FILE* h;
  readfile rf;
  char name[STRSIZE], suffix[STRSIZE], Xname[STRSIZE], Tname[STRSIZE], Zname[STRSIZE], 
       Xunitname[STRSIZE], Tunitname[STRSIZE], Zunitname[STRSIZE];
  int i, l, Tnumber, Rnumber, Rarraysize, Tarraysize, NR=(*qtab).NRho-1, NT=(*qtab).NT-1, 
      Xquantity, Xelement, Zquantity, Zelement, 
      Tfirst, Toriginal, Tlog, Rfirst, Roriginal, Rlog;
  double R, T, Tmin, Tmax, Rmin, Rmax, Tunit=(*units).T, Xunit, Zunit,
         *temperatures, *densities;

  printf( "\nCalculate mountain data:\n" );

  // Get density-temperature mesh parameters:
  sprintf(name,"%s.%s", file, PARFILE_SUFFIX);
  printf(" Read and check mesh parameters from source %s...", name);  
  GetMeshParameters( qtab, file, units, 1, &Rarraysize, &Tarraysize, &Rnumber, &Tnumber,
                     &Roriginal, &Rfirst, &Rlog, &Rmin, &Rmax,
                     &Toriginal, &Tfirst, &Tlog, &Tmin, &Tmax );
  printf(" done.\n");

  // Initialize density-temperature mesh:
  printf(" Initialize density-temperature mesh...");
  temperatures=dvector( 0, Tarraysize );    
  GetPointArray( (*qtab).T, NT, temperatures, &Tnumber, Toriginal, Tfirst, Tlog, Tmin, Tmax );
  densities=dvector( 0, Rarraysize ); 
  GetPointArray( (*qtab).Rho, NR, densities, &Rnumber, Roriginal, Rfirst, Rlog, Rmin, Rmax );
  printf(" done.\n");

  // Read and determine output quantities and units:
  printf(" Determine output-quantities from source %s...", name);
  GetOutputQuantity( qtab, file, units, fileformat, eostype, 
                     (char*)"Mountain", (char*)"Xquantity", (char*)"Xquantity",
                     &Xquantity, &Xunit, &Xelement, Xunitname, Xname );
  if(Xquantity>2) { printf( "\nSE-ERROR in Mountain ---> Invalid Xquantity input !!!\n" ); exit(0); }
  GetUnitsName( Tunitname, 3, 0, units );
  GetQuantityName( Tname, 3, 0, eostype );
  GetOutputQuantity( qtab, file, units, fileformat, eostype, 
                     (char*)"Mountain", (char*)"Quantity", (char*)"Element",
                     &Zquantity, &Zunit, &Zelement, Zunitname, Zname );
  if(Zquantity<4) { printf( "\nSE-ERROR in Mountain ---> Invalid Zquantity input !!!\n" ); exit(0); }
  printf(" done.\n");
  
  // Calculate and write mountain data:
  sprintf(suffix,"%s-%s-%s", Xname, Tname, Zname);
  sprintf(name,"%s.%s.%s", file, suffix, MOUNTAIN_SUFFIX);
  h = fopen(name,"w");  
  printf(" Table size (densities x temperatures): %d x %d\n", Rnumber, Tnumber );
  printf(" Processing table...");
  fflush( stdout );   
  fprintf( h, "# N%s  NT  N%s\n", Xname, Zname );  
  fprintf( h, "%d  %d  %d\n", Rnumber, Tnumber, Rnumber*Tnumber );
  fprintf(h, "&\n" );    
  fprintf( h, "# %s %s\n", Xname, Xunitname );
  for( l = 0; l<= Rnumber-1; l++ ) fprintf( h, "%e\n", (GetQuantity( Xquantity, qtab, densities[l], 0.0, 0, eostype, units )) / Xunit );
  fprintf(h, "&\n" );
  fprintf( h, "# %s %s\n", Tname, Tunitname );
  for( i = 0; i<= Tnumber-1; i++ ) fprintf( h, "%e\n", temperatures[i] / Tunit );
  fprintf(h, "&\n" );
  fprintf( h, "# %s %s\n", Zname, Zunitname );
  for( l = 0; l<= Rnumber-1; l++ )
  {
    R = densities[l];
    for ( i = 0; i <= Tnumber-1; i++ ) 
    {
	    T = temperatures[i];
	    fprintf(h,"%e\n", (GetQuantity( Zquantity, qtab, R, T, Zelement, eostype, units )) / Zunit );
    }
  }
  fprintf( h, "# eof." );
  printf(" done.\n");
  fclose(h);

  // Free memory and print final output to console: 
  free_dvector( temperatures,0,Tarraysize );   
  free_dvector( densities,0,Rarraysize );
  printf(" Wrote mountain data to file %s.\n", name);
  printf("Done.\n"); 
  
  return;
}

//////////////////////////////////////////////////////////////////

void Hugoniot(Qtable* qtab, char* file, Units* units, int fileformat, int eostype )
{
  FILE* h;
  readfile rf;
  char name[STRSIZE], Xname[STRSIZE], Xunitname[STRSIZE], Tname[STRSIZE], Tunitname[STRSIZE],
       Pname[STRSIZE], Punitname[STRSIZE], Ename[STRSIZE], Eunitname[STRSIZE],
       Uname1[STRSIZE], Uname2[STRSIZE], Uunitname1[STRSIZE], Uunitname2[STRSIZE];
  int NT = (*qtab).NT-1, Xquantity, Xelement; 
  double R,R0,T0,E0,P0,T,P,E,Us,Up,P_alt,PMAX,TMAX,Xunit,f,dx;  

  printf( "\nCalculate Hugoniot:\n" );

  // Read calculation parameters:
  sprintf(name,"%s.%s",file, PARFILE_SUFFIX);  
  printf(" Read Hugoniot parameters from source %s...", name);   
  rf.openinput(name);
  R0 = atof( rf.setget( (char*)"Hugoniot",(char*)"Rho0" ) ) * (*units).R;
  if(!Check_Density(qtab, R0, (*units).R)) exit(0);
  T0 = atof( rf.setget( (char*)"Hugoniot",(char*)"T0" ) ) * (*units).T;
  if(!Check_Temperature(qtab, T0, (*units).T)) exit(0);
  PMAX = atof( rf.setget( (char*)"Hugoniot",(char*)"Pmax" ) ) * (*units).P; 
  rf.closeinput();   
  GetOutputQuantity( qtab, file, units, fileformat, eostype, 
                     (char*)"Hugoniot", (char*)"Xquantity", (char*)"Xquantity",
                     &Xquantity, &Xunit, &Xelement, Xunitname, Xname );
  if(Xquantity>2) { printf( "\nSE-ERROR in Hugoniot ---> Invalid Xquantity input !!!\n" ); exit(0); }  
  printf(" done.\n");  

  // Get quantity names:
  GetUnitsName( Tunitname, 3, 0, units );
  GetQuantityName( Tname, 3, 0, eostype );
  GetUnitsName( Punitname, 4, 0, units );
  GetQuantityName( Pname, 4, 0, eostype );
  GetUnitsName( Eunitname, 5, 0, units );
  GetQuantityName( Ename, 5, 0, eostype );
  GetUnitsName( Uunitname1, 9, 0, units );
  GetQuantityName( Uname1, 9, 0, eostype );
  GetUnitsName( Uunitname2, 10, 0, units );
  GetQuantityName( Uname2, 10, 0, eostype );
  
  // Determine maximum temperature and initial pressure/energy:
  TMAX = (*qtab).T[NT];
  P0 = GetQuantity( 4, qtab, R0, T0, 0, eostype, units );  
  E0 = GetQuantity( 5, qtab, R0, T0, 0, eostype, units );
  printf(" Upper calculation boundary:\n");
  printf("  %smax = %e %s\n", Tname, TMAX / (*units).T, Tunitname);
  printf("  %smax = %e %s\n", Pname, PMAX / (*units).P, Punitname);
  printf(" Start point:\n");
  printf("  %s0 = %e %s\n", Xname, GetQuantity( Xquantity, qtab, R0, 0.0, 0, eostype, units ) / Xunit, Xunitname);
  printf("  %s0 = %e %s\n", Tname, T0 / (*units).T, Tunitname);
  printf("  %s0 = %e %s\n", Pname, P0 / (*units).P, Punitname);
  printf("  %s0 = %e %s\n", Ename, E0 / (*units).E, Eunitname);
 
  // Calculate and write Hugoniot curve:
  sprintf(name,"%s.%s", file, HUG_SUFFIX );
  h = fopen(name,"w");
  printf(" Processing Hugoniot...");
  fflush( stdout );  
  fprintf( h, "# %s %s  %s %s  %s %s  %s %s  %s %s  %s %s\n", 
           Xname, Xunitname, Tname, Tunitname, Pname, Punitname, 
           Ename, Eunitname, Uname1, Uunitname1, Uname2, Uunitname2 );         
  fprintf( h, "%e  %e  %e  %e  %e  %e\n", 
           (GetQuantity( Xquantity, qtab, R0, 0.0, 0, eostype, units ) / Xunit),
           T0/(*units).T, P0/(*units).P, E0/(*units).E, 0.0, 0.0 );
  R = R0; T = T0; P = P_alt = P0;
  while( T<TMAX && P<PMAX ) 
  { 
    do { 
      f  = fi( qtab, units, eostype, R, T, R0, E0, P0 );
      dx = HUG_FACTOR*f;   // Adjust this factor if no convergence ! 
      R = R + dx; 
      if (R<R0) 
      { 
	      printf( "\nSE-ERROR in Hugoniot ---> Imaginary sound velocity !!!\n" );
	      exit(0);
      }
    } while( fabs(f)/R0>1.0e-6);   // or: fabs(dx) > 1.0e-4
    P = GetQuantity( 4, qtab, R, T, 0, eostype, units );
    E = GetQuantity( 5, qtab, R, T, 0, eostype, units );
    Us = (1.0/R0)*sqrt( (P-P0)/(1.0/R0 - 1.0/R));
    Up = fabs(1.0- R0/R)*Us; 
    if (P>0.0 && fabs(P/P_alt) > P_MULT_HUG)     // don't save all steps
    {
      fprintf(h,"%e  %e  %e  %e  %e  %e\n", 
      	      (GetQuantity( Xquantity, qtab, R, 0.0, 0, eostype, units ) / Xunit),
              T/(*units).T,P/((*units).P),E/(*units).E,Us/(*units).U,Up/(*units).U ); 
      P_alt = P;
    }
    T *= T_MULT_HUG;
    R *= R_MULT_HUG;
  }
  fprintf( h, "# eof." );
  printf(" done.\n");
  fclose( h );

  // Print final output to console:   
  printf(" Wrote Hugoniot to file %s.\n", name);
  printf("Done.\n");
   
  return;
}

//////////////////////////////////////////////////////////////////

void SinglePoint( Qtable* qtab, char* rc, char* tc, Units* units, int fileformat, int eostype )
{
  char Qname[STRSIZE], Qunitname[STRSIZE], Tunitname[STRSIZE], Runitname[STRSIZE];
  int k;
  double R, T;
       
  R = atof(rc) * (*units).R;
  T = atof(tc) * (*units).T;
  if(!Check_Density(qtab, R, (*units).R)) exit(0);
  if(!Check_Temperature(qtab, T, (*units).T)) exit(0);  
  GetUnitsName( Runitname, 1, 0, units );
  GetUnitsName( Tunitname, 3, 0, units );

  printf( "\nSingle point info:\n" );  
  printf( " Rho = %e %s\n", R/(*units).R, Runitname);
  printf( " T = %e %s\n", T/(*units).R, Tunitname);
  GetUnitsName( Qunitname, 4, 0, units );
  GetQuantityName( Qname, 4, 0, eostype );
  printf(" %s = %+e %s\n", Qname, (GetQuantity( 4, qtab, R, T, 0, eostype, units ) / (*units).P), Qunitname );
  GetUnitsName( Qunitname, 5, 0, units );
  GetQuantityName( Qname, 5, 0, eostype );
  printf(" %s = %+e %s\n", Qname, (GetQuantity( 5, qtab, R, T, 0, eostype, units ) / (*units).E), Qunitname );
  GetUnitsName( Qunitname, 6, 0, units );
  GetQuantityName( Qname, 6, 0, eostype );
  printf(" %s = %+e %s\n", Qname, (GetQuantity( 6, qtab, R, T, 0, eostype, units ) / (*units).F), Qunitname );
  GetUnitsName( Qunitname, 7, 0, units );
  GetQuantityName( Qname, 7, 0, eostype );
  printf(" %s = %+e %s\n", Qname, (GetQuantity( 7, qtab, R, T, 0, eostype, units ) / (*units).S), Qunitname );
  if(fileformat==1) 
  {
    for(k=1; k<=(*qtab).Nelements; k++) 
    {
      GetQuantityName( Qname, 8, k, eostype );
      printf(" %s = %.4e for element Z[%d] = %.2f\n", Qname, (GetQuantity( 8, qtab, R, T, k, eostype, units ) / (*units).Q), k, (*qtab).Z[k-1] );  
    }
    if((*qtab).Nelements>1)
    {
      GetQuantityName( Qname, 8, 0, eostype );
      printf(" %s = %.4e for molecule Ztot = %.2f\n", Qname, (GetQuantity( 8, qtab, R, T, 0, eostype, units ) / (*units).Q), (*qtab).Ztot );    
    }
  }

  return;
}

//////////////////////////////////////////////////////////////////
// eof.