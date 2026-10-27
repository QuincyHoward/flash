//////////////////////////////////////////////////////////////////
// Main file of the FEOS table generation tool 
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#include "FE-00_DEFINITS.H"

//////////////////////////////////////////////////////////////////

int main(int argc, char** argv)
{ 
  // Variable declarations:
  char fname[STRSIZE], choice[STRSIZE], *name_in;
  int i, j, k, singlep, inerr, entitynumber, entity, matnumber, count,
      Tmaxwellunderrun, Tunderrun, Rhounderrun, BelowBinodal, maxwellcount,
      MaxwellFlag, SoftSphereFlag, UserCalculationsFlag,  
      *Rdensity, *Tdensity;
  double rho, t, p, e, s, f, *q, qtot, pe, ee, se, fe, pi, ei, si, fi,
         pTF, eTF, sTF, fTF, Rhostart, Tstart, Rhonorm, Tnorm, *TMaxwell;
  readfile rf;
  Qtable qtable;
  CriticalDataTable ctable;
  clock_t start, stop;


  // STEP 0 //////////////////////////////////////////////////////
  // Initial printout and initial library setup                 //
  ////////////////////////////////////////////////////////////////

  // Save starting time:
  start = clock();
    
  // Print header:
  printf("\nFEOS table generation tool 16.7\n");

  // Check if parameter file is specified:
  if(argc<2) {
    printf("\nUsage: feos <name of parameter file> [<rho(g/cm^3)> <T(eV)>]\n\n");
    exit(0);
  } 
  name_in = argv[1];

  // The FEOS table generation tool uses only one material entity:
  entitynumber = 1;
  printf("\nNumber of material entities: %d\n", entitynumber);

  // Initialize FEOS library:
  FEOS_Initialize(entitynumber, 1);
  

  // STEP 1 //////////////////////////////////////////////////////
  // Definition of all computational parameters                 //
  ////////////////////////////////////////////////////////////////

  // Define first point in temperature-density grid (for SESAME usually Rho0 = 0.0 and T0 = 0.0:
  Rhostart = Tstart = 0.0;

  // Read calculation parameters from parameter file:
  sprintf(fname, "%s.%s", name_in, PARFILE_SUFFIX);
  printf("\nRead parameters from source %s:\n", fname);
  rf.openinput(fname);
  //
  matnumber = atoi(rf.setget((char*)"Computation-Settings", (char*)"Material-Number"));
  printf(" Material number: %d\n", matnumber);
  //    
  MaxwellFlag = atoi(rf.setget((char*)"Computation-Settings", (char*)"Maxwell_Flag"));
  if(MaxwellFlag) printf(" Maxwell_Flag: Maxwell construction activated.\n");
  else printf(" Maxwell_Flag: No Maxwell construction.\n");
  //
  SoftSphereFlag = atoi(rf.setget((char*)"Computation-Settings", (char*)"SoftSphere_Flag"));
  if(SoftSphereFlag) printf(" SoftSphere_Flag: Soft-sphere function will be used.\n");
  else printf(" SoftSphere_Flag: No soft-sphere function.\n");
  //
  UserCalculationsFlag = atoi(rf.setget((char*)"Computation-Settings", (char*)"UserCalculations_Flag"));
  if(UserCalculationsFlag) printf(" UserCalculations_Flag: User-defined calculations will be performed.\n");
  else printf(" UserCalculations_Flag: No user-defined calculations.\n");
  //
  Rhonorm = atof(rf.setget((char*)"Q-table", (char*)"Rhonorm"));
  printf(" Rhonorm: %e g/cm^3\n", Rhonorm);
  //
  Rdensity = ivector(0, MAX_INTERVAL_RT_TABLE);
  getPointDensity(&rf, Rdensity, &(qtable.NRho), (char*)key_RR);
  printf(" Total number of density points (includes Rho0 = %.2e g/cm^3): %d\n", Rhostart, qtable.NRho);
  //
  Tnorm = atof(rf.setget((char*)"Q-table", (char*)"Tnorm"));
  printf(" Tnorm: %e eV\n", Tnorm);
  //    
  Tdensity = ivector(0, MAX_INTERVAL_RT_TABLE);
  getPointDensity(&rf,Tdensity, &(qtable.NT), (char*)key_TR);
  printf(" Total number of temperature points (includes T0 = %.2e eV): %d\n", Tstart, qtable.NT);
  //
  rf.closeinput();      
  printf("Done.\n");


  // STEP 2 //////////////////////////////////////////////////////
  // Definition of all required density and temperature tables  //
  ////////////////////////////////////////////////////////////////

  // Get library calculation limits:
  FEOS_Get_Calc_Limits( &(qtable.Tcalclimit), &(qtable.Rhocalclimit) );

  // Allocate memory for EOS-table:
  GetQTABmemory1(&qtable);
    
  // Initialize EOS-table structure:
  printf("\nInitialize EOS-table structure:\n");
  //
  makeRTPointArray(Rdensity, qtable.Rho, Rhonorm, Rhostart);
  makeRTPointArray(Tdensity, qtable.T, Tnorm, Tstart);
  //  
  printf(" Table size (densities x temperatures): %d x %d\n Table boundaries (density, temperature):\n", qtable.NRho, qtable.NT);
  printf("  (%e g/cm^3, %e eV) ...\n", qtable.Rho[0], qtable.T[0]);
  if(qtable.NRho>2 && qtable.NT<3) printf("  ... (%e g/cm^3, %e eV) ...\n", qtable.Rho[1], qtable.T[0]);
  else if(qtable.NRho<3 && qtable.NT>2) printf("  ... (%e g/cm^3, %e eV) ...\n", qtable.Rho[0], qtable.T[1]);
  else if(qtable.NRho>2 && qtable.NT>2) printf("  ... (%e g/cm^3, %e eV) ...\n", qtable.Rho[1], qtable.T[1]);
  printf("  ... (%e g/cm^3, %e eV)\n", qtable.Rho[qtable.NRho-1], qtable.T[qtable.NT-1]);  
  printf("Done.\n");
  
  // Allocate memory for Maxwell-temperature table:
  TMaxwell = dvector(0, qtable.NT-1);

  // Initialize Maxwell-temperature table structure (here same points as for EOS):
  printf("\nInitialize Maxwell-temperature table structure:\n");
  for(i=0; i<qtable.NT; i++) TMaxwell[i] = qtable.T[i];
  printf(" Same temperatures used as for EOS calculation!\nDone.\n");  

  // Check EOS- and Maxwell-table temperatures and densities:
  printf("\nCheck table structures:\n");
  Tunderrun = Rhounderrun = 0;
  for( i=0; i<qtable.NRho; i++) { if( qtable.Rho[i]*(1.0+1.0e-7)<qtable.Rhocalclimit ) Rhounderrun++; }
  for( j=0; j<qtable.NT; j++) { if( qtable.T[j]*(1.0+1.0e-7)<qtable.Tcalclimit ) Tunderrun++; }
  if(Tunderrun) { 
    printf(" WARNING: %d temperature", Tunderrun);
    if(Tunderrun>1) printf("s");
    printf(" below library calculation limit %.2e eV!\n", qtable.Tcalclimit);
  }
  if(Rhounderrun) {
    printf(" WARNING: %d densit", Rhounderrun);
    if(Rhounderrun>1) { printf("ies"); } else { printf("y"); }
    printf(" below library calculation limit %.2e g/cm^3!\n", qtable.Rhocalclimit);
  }
  if(!Tunderrun && !Rhounderrun) printf( " Everything ok!\n");
  printf("Done.\n");
  

  // STEP 3 //////////////////////////////////////////////////////
  // Material initialization                                    //
  ////////////////////////////////////////////////////////////////

  // The FEOS user interface uses only one material:
  entity = 1;           

  // Initialize material:
  FEOS_Init_Mat(entity, matnumber, MaxwellFlag, SoftSphereFlag, TMaxwell, qtable.NT, 
                      &(qtable.Nelements), &(ctable.Niso), &(ctable.Trel));  

  // Get material parameters:
  GetQTABmemory2(&qtable, 0);
  FEOS_Get_Mat_Par(entity, qtable.A, qtable.Z, qtable.X, &(qtable.Atot), &(qtable.Ztot), &(qtable.Xtot), 
                         &(qtable.TRef), &(qtable.RhoRef), &(qtable.BulkModulusRef), &(qtable.SESAMEnumber));
  FEOS_Get_Energy_Offsets( entity, &(qtable.ElectronOffset), &(qtable.IonOffset) );
  if(SoftSphereFlag) FEOS_Get_SoftSphere_Par(entity, &(qtable.Ecoh), &(qtable.softsphere_n), &(qtable.softsphere_m),
                                                   &(qtable.softsphere_A), &(qtable.softsphere_B));                       
                         
  // If initialized, get critical parameters:
  if(ctable.Niso > 0) {                         
    GetCTABmemory(&ctable);
    FEOS_Get_Crit_Point(entity, &(ctable.Tc), &(ctable.Rhoc), &(ctable.Pc), &(ctable.Hc), &(ctable.Sc), &(ctable.Zc));
    FEOS_Get_Binodal(entity, ctable.Tiso, ctable.Peq, ctable.Rhol, ctable.Rhov, ctable.Pl, ctable.Pv, 
                           ctable.Gl, ctable.Gv, ctable.Hl, ctable.Hv, ctable.Zl, ctable.Zv, &(ctable.Tb));
    FEOS_Get_Spinodal(entity, ctable.Tiso, ctable.Rhomin, ctable.Rhomax, ctable.Pmin, ctable.Pmax);
  }
  

  // STEP 4 //////////////////////////////////////////////////////  
  // STEP 4a: Computation/printout of EOS data for single point //
  // STEP 4b: Computation/printout of EOS-table data,           //
  //          eventually followed by user-defined calculations  //
  ////////////////////////////////////////////////////////////////
  
  // STEP 4a: If three arguments present, print single point info onto console:
  if (argc==4) {
    q = dvector(0, qtable.Nelements-1);  
    singlep = inerr = 0;
    while(singlep!=2) {
      // Input of the user:
      if(singlep == 0) {
        singlep = 1;
        rho = atof(argv[2]);
        t = atof(argv[3]);
        if(rho<0.0 || t<0.0) {
          printf("\nNo single point info available for negative Rho or T!\n");
          printf(" Rho = %e g/cm^3, T = %e eV\n", rho, t);
          singlep = 3;
        }
      }
      else {
        printf("\nNext single point info? (exit with negative Rho or T)\n");
        do {
          inerr = 0; singlep = 1;
          printf(" Rho [g/cm^3]: ");
          cin >> rho; 
          if(cin.fail()) {  
            inerr = 1; 
            printf("  Wrong input: Not a number! (exit with negative Rho)\n");
            cin.clear(); cin.ignore(80, '\n');
          }
          if(rho<0.0) singlep = 2;
        } while(inerr);
        if(singlep!=2) {
          do {
            inerr = 0; singlep = 1;
            printf(" T [eV]: ");
            cin >> t; 
            if(cin.fail()) {  
              inerr = 1; 
              printf("  Wrong input: Not a number! (exit with negative T)\n");
              cin.clear(); cin.ignore(80, '\n');
            }
            if(t<0.0) singlep = 2;
          } while(inerr);        
        }
        if(singlep!=2 && ctable.Niso>0) {
          do {
            inerr = 0; singlep = 1;
            printf(" Maxwell construction (yes/no): ");
            cin >> choice; 
            if(!strcmp(choice,"y") || !strcmp(choice,"Y") || !strcmp(choice,"yes") || !strcmp(choice,"Yes") ||  
               !strcmp(choice,"yEs") || !strcmp(choice,"yeS") || !strcmp(choice,"YEs") || !strcmp(choice,"YeS") ||
               !strcmp(choice,"yES") || !strcmp(choice,"YES")) MaxwellFlag = 1;
            else if(!strcmp(choice,"n") || !strcmp(choice,"N") || !strcmp(choice,"no") || 
                    !strcmp(choice,"No") || !strcmp(choice,"nO") || !strcmp(choice,"NO")) MaxwellFlag = 0;
            else {
              inerr = 1; 
              printf("  Wrong input: Type 'y' or 'n'!\n");
              cin.clear(); cin.ignore(80, '\n');
            }
          } while(inerr);           
        }
      }

      // Calculation for the given density-temperature point:
      if(singlep<2) {
        printf("\nSingle point info for Rho = %e g/cm^3 and T = %e eV:\n", rho, t);
        // Calculate EOS for one point:
        FEOS_Get_EOS_All( entity, MaxwellFlag, rho, t, &BelowBinodal, &p, &e, &s, &f, q, &qtot, 
				                        &pe, &ee, &se, &fe, &pi, &ei, &si, &fi, &pTF, &eTF, &sTF, &fTF );
				// Print warnings:                       
        if(rho*(1.0+1.0e-7) < qtable.Rhocalclimit) printf(" WARNING: Rho = %.2e g/cm^3 below library calculation limit %.2e g/cm^3!\n", rho, qtable.Rhocalclimit);
        if(t*(1.0+1.0e-7) < qtable.Tcalclimit) printf(" WARNING: T = %.2e eV below library calculation limit %.2e eV!\n", t, qtable.Tcalclimit);
        if(MaxwellFlag && t*(1.0+1.0e-7) < ctable.Trel) printf(" WARNING: T = %.2e eV below reliable Maxwell construction data!\n", t);
        // Print general information:
        if(MaxwellFlag && BelowBinodal) printf(" Density-temperature point lies inside the two-phase region!\n -> Calculation done with Maxwell construction!\n");
        else if(MaxwellFlag) printf(" Density-temperature point lies outside the two-phase region!\n -> Calculation done without Maxwell construction!\n");
        else printf(" Calculation done without Maxwell construction!\n");  
        if(SoftSphereFlag && rho < qtable.RhoRef) printf(" Calculation done with soft-sphere function (Rho < %e g/cm^3)!\n", qtable.RhoRef);
        else if(SoftSphereFlag && rho >= qtable.RhoRef) printf(" Calculation done without soft-sphere function (Rho >= %e g/cm^3)!\n", qtable.RhoRef);
        else printf(" Calculation done without soft-sphere function!\n");
        // Print EOS: 
        printf(" P = %+e (Pi = %+e, Pe = %+e) [dyne/cm^2]\n", p, pi, pe );
        printf(" E = %+e (Ei = %+e, Ee = %+e) [erg/g]\n", e, ei, ee );
        printf(" F = %+e (Fi = %+e, Fe = %+e) [erg/g]\n", f, fi, fe );
        printf(" S = %+e (Si = %+e, Se = %+e) [erg/(g*eV)]\n", s, si, se );
        printf(" Ei~Fi_Offset = %+e, Ee~Fe_Offset = %+e [erg/g]\n", qtable.IonOffset, qtable.ElectronOffset );
        for(k=0; k<qtable.Nelements; k++) printf(" Q[%d] = %.4e for element Z[%d] = %.2f\n", k+1, q[k], k+1, qtable.Z[k] );
        if(qtable.Nelements>1) printf(" Qtot = %.4e for molecule Ztot = %.2f\n", qtot, qtable.Ztot );
      }
    }
    free_dvector(q,0,qtable.Nelements-1);
  }
  
  // STEP 4B: Else calculate EOS-table data, write it into files, and eventually perform user-defined calculations:    
  else {
    // Compute the EOS-table for all points:  
    printf("\nCompute EOS-table data:\n"); 
    printf(" Processing temperature [eV]:\n");
    Tmaxwellunderrun = maxwellcount = count = 0;
    printf(" ");
    for( j=0; j<qtable.NT; j++) {
      printf(" %e", qtable.T[j]);
      fflush( stdout );
      if(qtable.T[j]*(1.0+1.0e-7) < ctable.Trel) Tmaxwellunderrun++;
      for( i=0; i<qtable.NRho; i++) {
	      FEOS_Get_EOS_All( entity, MaxwellFlag, qtable.Rho[i], qtable.T[j], &BelowBinodal,
				  &(qtable.P[i][j]), &(qtable.E[i][j]), &(qtable.S[i][j]), &(qtable.F[i][j]), qtable.Q[i][j], &(qtable.Qtot[i][j]),
          &(qtable.Pe[i][j]), &(qtable.Ee[i][j]), &(qtable.Se[i][j]), &(qtable.Fe[i][j]),
          &(qtable.Pi[i][j]), &(qtable.Ei[i][j]), &(qtable.Si[i][j]), &(qtable.Fi[i][j]),
          &(qtable.PTF[i][j]), &(qtable.ETF[i][j]), &(qtable.STF[i][j]), &(qtable.FTF[i][j]) );
        if(BelowBinodal) maxwellcount++;                             
      }
      count++;
      if(j==qtable.NT-1) printf(".\n");
      else if(count%5) printf(",");
      else printf(",\n ");
    }

    // Print warnings:
    if(Tunderrun || Rhounderrun) {
      printf(" WARNING: %d density-temperature point",Tunderrun*(qtable.NRho)+Rhounderrun*(qtable.NT-Tunderrun));
      if((Tunderrun*(qtable.NRho)+Rhounderrun*(qtable.NT-Tunderrun))>1) printf("s");
      printf(" below library calculation limits!\n");
    }
    if(MaxwellFlag && Tmaxwellunderrun) {
      printf(" WARNING: %d temperature set",Tmaxwellunderrun);
      if(Tmaxwellunderrun>1) printf("s");
      printf(" below reliable Maxwell construction data!\n");    
    }

    // Print two-phase information:
    if(MaxwellFlag) {
      printf(" %d density-temperature point",maxwellcount);
      if(maxwellcount!=1) printf("s");
      printf(" lie inside the two-phase region.\n");    
    }  
    printf("Done.\n");

    // Write calculated EOS data into files:
    if(ctable.Niso > 0) write_criticaldata(name_in, &ctable, MaxwellFlag, qtable.Atot, qtable.Xtot); 
    write_FEOS_format( name_in, &qtable );
    write_mexport_format( name_in, &qtable );
    write_301_format( name_in, &qtable );
    write_304_format( name_in, &qtable );
    write_305_format( name_in, &qtable );
    write_txt_format( name_in, &qtable );
    write_Rostock_format( name_in, &qtable );    

    // If UserCalculations_Flag is set on, perform used-defined calculations:
    if(UserCalculationsFlag) {
      printf("\n====================== Start user-defined calculations ======================\n");
      UserCalculations( entity, name_in, &qtable, &ctable );
      printf("\n======================= End user-defined calculations =======================\n");
    }
  }


  // STEP 5 //////////////////////////////////////////////////////
  // Free all memory, finalize library, and printout runtime    //
  ////////////////////////////////////////////////////////////////
 
  // Finalize library (free library memory): 
  FEOS_Finalize( );
  
  // Free all memory used by the FEOS table generation tool:
  printf("\nFree all memory...");
  FreeQTABmemory(&qtable, 0);
  if(ctable.Niso > 0) FreeCTABmemory(&ctable);    
  free_ivector(Rdensity, 0, MAX_INTERVAL_RT_TABLE); 
  free_ivector(Tdensity, 0, MAX_INTERVAL_RT_TABLE);
  free_dvector(TMaxwell, 0, qtable.NT-1);
  printf(" done.\n");
  
  // Print cpu runtime:
  stop = clock();  
  printf("\nCPU runtime: %.2f seconds\n\n", (double)(stop-start)/CLOCKS_PER_SEC);
        
  return 0;
}

//////////////////////////////////////////////////////////////////
// eof.