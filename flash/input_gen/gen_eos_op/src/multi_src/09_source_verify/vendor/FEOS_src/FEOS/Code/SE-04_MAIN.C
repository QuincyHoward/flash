//////////////////////////////////////////////////////////////////
// Main file of the SHOWEOS table visualization tool 
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#include "SE-00_DEFINITS.H"

//////////////////////////////////////////////////////////////////

int main(int argc, char** argv )
{
  // Variable declarations:
  Qtable qtable;
  readfile rf;
  Units units;
  char name[STRSIZE], *name_in = NULL;
  int type_in, eostype, fileformat;
  clock_t start, stop;


  // STEP 0 //////////////////////////////////////////////////////
  // Initial printout and argument check-up                     //
  ////////////////////////////////////////////////////////////////

  // Save starting time:
  start = clock();

  // Print header:
  printf("\nSHOWEOS table visualization tool 16.7\n");
  
  // Check if parameter file and correct option is specified:  
  if(argc<2) printf( "\nUsage: showeos <name of parameter file> <option> [<rho(Rho_unit)> <T(T_unit)>]\n" );
  else name_in = argv[1];
  if(argc==2) printf( "\nUsage: showeos %s <option> [<rho(Rho_unit)> <T(T_unit)>]\n", name_in );   
  type_in = 0;
  if(argc>2) type_in = atoi(argv[2]);
  if(type_in > 6) type_in = 0;    
  if(!type_in) {
    printf( "\nPossible values for <option> are:\n 1 for Isotherms\n 2 for Isochores\n" );
    printf( " 3 for Isentropes\n 4 for Mountain-Plot\n 5 for Hugoniot-Curves\n" );
    printf( " 6 <rho(Rho_unit)> <T(T_unit)> for a single point info\n\n" );
    exit(0); 
  }
  if(type_in==6 && argc<5) {
    printf("\nUsage: showeos %s 6 <rho(Rho_unit)> <T(T_unit)>\n\nValues for Rho and T are not correctly specified.\n\n", name_in );
    exit(0); 
  }  


  // STEP 1 //////////////////////////////////////////////////////
  // Read and check general parameters from the parameter file  //
  ////////////////////////////////////////////////////////////////

  sprintf(name,"%s.%s",name_in, PARFILE_SUFFIX);
  printf("\nRead and check general parameters and units from source %s...", name);
  rf.openinput(name);
  fileformat = atoi( rf.setget( (char*)"General", (char*)"File-Format" ));
  if(fileformat != 1 && fileformat != 2) { printf( "\nWrong Input for File-Format !!!\n" ); exit(0); }
  eostype = atoi( rf.setget( (char*)"General", (char*)"EOS-Type" ));
  if(eostype<1 || eostype>4 || (eostype == 4 && fileformat == 2)) { printf( "\nWrong Input for EOS-Type !!!\n" ); exit(0); }  
  units.R = atof( rf.setget( (char*)"Units", (char*)"Rho_unit" ) );
  units.T = atof( rf.setget( (char*)"Units", (char*)"T_unit" ) );
  units.P = atof( rf.setget( (char*)"Units", (char*)"P_unit" ) ); 
  units.E = atof( rf.setget( (char*)"Units", (char*)"E_unit" ) );
  units.U = atof( rf.setget( (char*)"Units", (char*)"U_unit" ) );
  if(units.R<=0.0 || units.T<=0.0 || units.P<=0.0 || units.E<=0.0 || units.U<=0.0) {
    printf( "\nAll units must be greater zero !!!\n" ); exit(0);
  }
  rf.closeinput();
  units.S = units.E / units.T;
  units.F = units.E;
  units.V = 1.0 / units.R;
  units.Q = 1.0;
  printf(" done.\n");
  
  
  // STEP 2 //////////////////////////////////////////////////////
  // Read EOS table (routines in SE-01_READTABLE.C)             //
  ////////////////////////////////////////////////////////////////  

  switch( fileformat ) {
    case 1 : read_FEOS_format( name_in, &qtable, &units ); break;
    case 2 : {
      switch( eostype ) {
        case 1 : read_301_format( name_in, &qtable, &units ); break;
        case 2 : read_304_format( name_in, &qtable, &units ); break;
        case 3 : read_305_format( name_in, &qtable, &units ); break;
        default : printf( "\nSE-ERROR in main ---> Unexpected error !!!\n" ); exit(0); 
      } } break;
    default : printf( "\nSE-ERROR in main ---> Unexpected error !!!\n" ); exit(0); 
  }
  
  
  // STEP 3 //////////////////////////////////////////////////////
  // Perform desired action (routines in SE-03_SERVICES.C)      //
  ////////////////////////////////////////////////////////////////  
  
  switch( type_in ) {
    case 1 : Isotherms( &qtable, name_in, &units, fileformat, eostype ); break;
    case 2 : Isochores( &qtable, name_in, &units, fileformat, eostype ); break;
    case 3 : Isentropes( &qtable, name_in, &units, fileformat, eostype ); break;
    case 4 : Mountain( &qtable, name_in, &units, fileformat, eostype ); break;
    case 5 : Hugoniot( &qtable, name_in, &units, fileformat, eostype ); break;
    case 6 : SinglePoint( &qtable, argv[3], argv[4], &units, fileformat, eostype ); break;
    default : printf( "\nSE-ERROR in main ---> Unexpected error !!!\n" ); exit(0); 
  }


  // STEP 4 //////////////////////////////////////////////////////
  // Free all memory and printout runtime                       //
  ////////////////////////////////////////////////////////////////

  // Free all memory used by the SHOWEOS table visualization tool:
  printf("\nFree all memory...");
  FreeQTABmemory(&qtable, 1);
  printf(" done.\n");
    
  // Print cpu runtime:
  stop = clock();  
  printf("\nCPU runtime: %.2f seconds\n\n", (double)(stop-start)/CLOCKS_PER_SEC);
  
  return 0;
}

//////////////////////////////////////////////////////////////////  
// eof.