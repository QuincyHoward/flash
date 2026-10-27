//////////////////////////////////////////////////////////////////
// C/C++ interface routines of the FEOS library  
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#include "LIB-00_DEFINITS.H"  
#include "LIB-05_EOS_SERVICES.H"
#include "LIB-06_MAXWELL.H" 
#include "libfeos.h"
  
//////////////////////////////////////////////////////////////////

namespace NSP_FEOS_LIB 
{
  Ionpart** ionpart;
  QIPscheme*** qipscheme;
  CriticalData** Critical;
  int* InitFlag;
  int entityanz = 0;
  int PrintFlag = 0;
}

//////////////////////////////////////////////////////////////////

int Check_Lib_Init( char* callingroutine )
{
  using namespace NSP_FEOS_LIB;  

  if(entityanz<1) {
   	printf("\nLIB-ERROR in %s ---> FEOS library was not initialized !!!\n", callingroutine);
	  return 0;
	}	  
  return 1;
}

//////////////////////////////////////////////////////////////////

int Check_Mat_Entity( int entity, char* callingroutine )
{
  using namespace NSP_FEOS_LIB;
  
  if(!Check_Lib_Init(callingroutine)) return 0;

 	if(entity<1 || entity>entityanz) {
   	printf("\nLIB-ERROR in %s ---> Material entity number %d does not lie in range 1...%d !!!\n", callingroutine, entity, entityanz);
	  return 0; 
  }  
  return 1;
}

//////////////////////////////////////////////////////////////////

int Check_Mat_Init( int entity, char* callingroutine )
{
  using namespace NSP_FEOS_LIB;
  
  if(!Check_Mat_Entity(entity, callingroutine)) return 0;

  if(!InitFlag[entity-1]) {
   	printf("\nLIB-ERROR in %s ---> Material entity %d was not initialized !!!\n", callingroutine, entity);
	  return 0;
	}
	return 1;
}

//////////////////////////////////////////////////////////////////

int Check_Maxwell_Init( int entity, char* callingroutine )
{
  using namespace NSP_FEOS_LIB;
  
  if(!Check_Mat_Init(entity, callingroutine)) return 0;

  if(!(*ionpart[entity-1]).MaxwellFlag || !(*Critical[entity-1]).data.Niso) { 
    printf( "\nLIB-ERROR in %s ---> No Maxwell construction data available for material entity %d\n", callingroutine, entity );
    return 0;
  }
	return 1;
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Initialize( int entitynumber, int printflag )
{
  using namespace NSP_FEOS_LIB;
  int i;

  PrintFlag = printflag;

  if(PrintFlag) printf("\n=> Initialize FEOS library 16.7-beta...");
  
  if(entitynumber<1) {
   	printf("\nLIB-ERROR in FEOS_Initialize ---> Number of entities < 1 !!!\n");
	  exit(0);  
  }
  if(entityanz==0) {
    entityanz = entitynumber;
    ionpart = new Ionpart*[entityanz];
    qipscheme = new QIPscheme**[entityanz];
    Critical = new CriticalData*[entityanz];
    InitFlag = new int[entityanz];
    for(i=0; i<entityanz; i++) InitFlag[i] = 0;
  }
  else {
   	printf("\nLIB-ERROR in FEOS_Initialize ---> Library is already initialized !!!\n");
	  exit(0);     
  }
  
  if(PrintFlag) printf("\n<= FEOS library successfully initialized.\n");  
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Finalize( )
{
  using namespace NSP_FEOS_LIB;
  int i;

  if(entityanz>0) {
    if(PrintFlag) printf("\n=> Finalize FEOS library...");
  
    for(i=1; i<=entityanz; i++) {
      if(InitFlag[i-1]) { if(PrintFlag) { printf("\n"); } }
      FEOS_Delete_Mat(i);
    }  
    delete qipscheme;
    delete ionpart;
    delete Critical;
    delete InitFlag;
    entityanz = 0;

    if(PrintFlag) printf("\n<= FEOS library successfully finalized.\n");
  }

  PrintFlag = 0;
    
  return; 
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Get_Calc_Limits( double* Tzero, double* Rhozero )
{ 
  using namespace NSP_FEOS_LIB;
  char routinename[STRSIZE] = "FEOS_Get_Calc_Limits";

  if(!Check_Lib_Init(routinename)) exit(0);

  *Tzero = T_ZERO;
  *Rhozero = RHO_ZERO;
    
  if(PrintFlag) printf("\n<=> Library calculation limits successfully passed.\n");    
	return;
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Init_Mat( int entity, int materialnumber, int Maxwellflag, int softsphereflag, double* MaxwellTtab,  
                                 int sizeofMaxwellTtab, int* numofelements, int* numofMaxwelliso, double* MaxwellTreliable )
{
  using namespace NSP_FEOS_LIB;
  char routinename[STRSIZE] = "FEOS_Init_Mat";
  double pe_solid, dpedr_solid, Ee_solid, pe_zero, Ee_zero;
  int i;
	
  if(PrintFlag) printf("\n=> Initialize material entity %d...\n", entity);

  if(!Check_Mat_Entity(entity, routinename)) exit(0);
	
  if(InitFlag[entity-1] == 0) {  
    // Check material number and Maxwell input:
    if(materialnumber<1000 || materialnumber >9999){
   	  printf("\nLIB-ERROR in FEOS_Init_Mat ---> Material number %d outside database boundaries !!!\n", materialnumber);    
      exit(0);    
    }  
    if(sizeofMaxwellTtab<0) {
	    printf("\nLIB-ERROR in FEOS_Init_Mat ---> Number of isotherms for Maxwell construction < 0 !!!\n");
	    exit(0);
	  } 
    if(Maxwellflag && sizeofMaxwellTtab<1) {
	    printf("\nLIB-ERROR in FEOS_Init_Mat ---> Number of isotherms for Maxwell construction < 1 !!!\n");
	    exit(0);
  	}
     
    // Initialise IonPart with data file (Material database read from MATERIAL_DATABASE_PATH):
    if(PrintFlag) printf("\n Initialize Ionpart:\n");
    ionpart[entity-1] = new Ionpart(materialnumber, Maxwellflag, softsphereflag, PrintFlag);
    *numofelements = (*ionpart[entity-1]).Nelements;
    if(PrintFlag) printf(" Ionpart successfully initialized.\n");  

    // Initialize QIPscheme for every element (TF-Table read from TF_TABLE_PATH)
    qipscheme[entity-1] = new QIPscheme*[(*ionpart[entity-1]).Nelements];
    for(i=0; i<(*ionpart[entity-1]).Nelements; i++) {
	    if(PrintFlag) printf("\n Initialize QIPscheme for element %d (A = %f, Z = %f):", i+1, (*ionpart[entity-1]).Aelement[i], (*ionpart[entity-1]).Zelement[i]);
      qipscheme[entity-1][i] = new QIPscheme((char*)TF_TABLE_PATH, (*ionpart[entity-1]).Aelement[i], (*ionpart[entity-1]).Zelement[i], PrintFlag);
	    if(PrintFlag) printf(" QIPscheme for element %d successfully initialized.\n", i+1);
    }
		       
    // Compute dP/dRho at reference temperature and reference density for electronic contribution:
    mixture_getdpdr_solid(qipscheme[entity-1], ionpart[entity-1], &pe_solid, &Ee_solid, &dpedr_solid, &pe_zero, &Ee_zero);

    // Initialise bonding contribution with reference data:
    (*ionpart[entity-1]).getBondingParameters(pe_solid, dpedr_solid, Ee_solid, pe_zero, Ee_zero);

    // Initialise critical data and perform Maxwell construction if needed:    
    Critical[entity-1] = new CriticalData(ionpart[entity-1], qipscheme[entity-1], MaxwellTtab, sizeofMaxwellTtab);
    *numofMaxwelliso = (*Critical[entity-1]).data.Niso;
    *MaxwellTreliable = (*Critical[entity-1]).data.Trel;         
  }
  else {
   	printf("\nLIB-ERROR in FEOS_Init_Mat ---> Material entity %d is already initialized !!!\n", entity);
	  exit(0);
  }

  InitFlag[entity-1] = 1;
  if(PrintFlag) printf("\n<= Material entity %d successfully initialized.\n", entity);  
  return;   
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Delete_Mat( int entity )
{
  using namespace NSP_FEOS_LIB;
  char routinename[STRSIZE] = "FEOS_Delete_Mat";
  int i;

  if(!Check_Mat_Entity(entity, routinename)) exit(0);

  if(InitFlag[entity-1] != 0) {
    for(i=0; i<(*ionpart[entity-1]).Nelements; i++) delete qipscheme[entity-1][i];
    delete qipscheme[entity-1];
    delete ionpart[entity-1];
    delete Critical[entity-1];
    InitFlag[entity-1] = 0;
    if(PrintFlag) printf("\n<=> Material entity %d successfully deleted.\n", entity); 
  }
  
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Get_Mat_Par( int entity, double* A, double* Z, double* X, double* Atot, double* Ztot, double* Xtot,                              
                             double* Tref, double* Rhoref, double* BulkModref, int* SESAMEnumber )
{
  using namespace NSP_FEOS_LIB;
  char routinename[STRSIZE] = "FEOS_Get_Mat_Par";
  int i;

  if(!Check_Mat_Init(entity, routinename)) exit(0);

  for(i=0; i<(*ionpart[entity-1]).Nelements; i++) {
    A[i] = (*ionpart[entity-1]).Aelement[i];
    Z[i] = (*ionpart[entity-1]).Zelement[i];
    X[i] = (*ionpart[entity-1]).Xelement_tot[i]; 
  }
  
  *Atot = (*ionpart[entity-1]).Atot;
  *Ztot = (*ionpart[entity-1]).Ztot;  
  *Xtot = (*ionpart[entity-1]).Xtot;
  *Tref = (*ionpart[entity-1]).T_standard;
  *Rhoref = (*ionpart[entity-1]).rhosolid;
  *BulkModref = (*ionpart[entity-1]).BulkModulus;
  *SESAMEnumber = (*ionpart[entity-1]).SESAMEnumber;  

  if(PrintFlag) printf("\n<=> Material parameters of material entity %d successfully passed.\n", entity);     
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Get_SoftSphere_Par( int entity, double* Ecoh, double* softsp_n, double* softsp_m, double* softsp_A, double* softsp_B  )
{
  using namespace NSP_FEOS_LIB;
  char routinename[STRSIZE] = "FEOS_Get_SoftSphere_Par";
  
  if(!Check_Mat_Init(entity, routinename)) exit(0);

  if(!(*ionpart[entity-1]).SoftSphereFlag) { 
    printf( "\nLIB-ERROR in FEOS_Get_SoftSphere_Par ---> No soft-sphere parameters available for material entity %d\n", entity );
    exit(0);
  }

  *Ecoh = (*ionpart[entity-1]).E_cohesive;
  *softsp_n = (*ionpart[entity-1]).softsphere_n;
  *softsp_m = (*ionpart[entity-1]).softsphere_m;
  *softsp_A = (*ionpart[entity-1]).softsphere_A;
  *softsp_B = (*ionpart[entity-1]).softsphere_B;        

  if(PrintFlag) printf("\n<=> Soft-sphere parameters of material entity %d successfully passed.\n", entity);    
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Get_Energy_Offsets( int entity, double* ElectronOffs, double* IonOffs )
{
  using namespace NSP_FEOS_LIB;
  char routinename[STRSIZE] = "FEOS_Get_Energy_Offsets";

  if(!Check_Mat_Init(entity, routinename)) exit(0);

  *ElectronOffs = (*ionpart[entity-1]).Ee_Offset;
  *IonOffs = (*ionpart[entity-1]).Ei_Offset;  

  if(PrintFlag) printf("\n<=> Energy offsets of material entity %d successfully passed.\n", entity);
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Get_Crit_Point( int entity, double* T, double* Rho, double* P, double* H, double* S, double* Z )
{
  using namespace NSP_FEOS_LIB;
  char routinename[STRSIZE] = "FEOS_Get_Crit_Point";

  if(!Check_Maxwell_Init(entity, routinename)) exit(0);

  *T = (*Critical[entity-1]).data.Tc;
  *Rho = (*Critical[entity-1]).data.Rhoc;
  *P = (*Critical[entity-1]).data.Pc;
  *H = (*Critical[entity-1]).data.Hc;
  *S = (*Critical[entity-1]).data.Sc;
  *Z = (*Critical[entity-1]).data.Zc;          

  if(PrintFlag) printf("\n<=> Critical point of material entity %d successfully passed.\n", entity);
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Get_Binodal( int entity, double* T, double* P, double* Rholiq, double* Rhovap, double* Pliq, double* Pvap, 
                                    double* Gliq, double* Gvap, double* Hliq, double* Hvap, double* Zliq, double* Zvap, double* Tboil )
{
  using namespace NSP_FEOS_LIB;
  char routinename[STRSIZE] = "FEOS_Get_Get_Binodal";
  int i;

  if(!Check_Maxwell_Init(entity, routinename)) exit(0);

  for(i=0; i<(*Critical[entity-1]).data.Niso; i++) {
    T[i] = (*Critical[entity-1]).data.Tiso[i];
    P[i] = (*Critical[entity-1]).data.Peq[i];
    Rholiq[i] = (*Critical[entity-1]).data.Rhol[i];
    Rhovap[i] = (*Critical[entity-1]).data.Rhov[i];
    Pliq[i] = (*Critical[entity-1]).data.Pl[i];
    Pvap[i] = (*Critical[entity-1]).data.Pv[i];
    Gliq[i] = (*Critical[entity-1]).data.Gl[i];
    Gvap[i] = (*Critical[entity-1]).data.Gv[i];
    Hliq[i] = (*Critical[entity-1]).data.Hl[i];
    Hvap[i] = (*Critical[entity-1]).data.Hv[i];
    Zliq[i] = (*Critical[entity-1]).data.Zl[i];
    Zvap[i] = (*Critical[entity-1]).data.Zv[i];
  }
  
  *Tboil = (*Critical[entity-1]).data.Tb;

  if(PrintFlag) printf("\n<=> Binodal of material entity %d successfully passed.\n", entity);
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Get_Spinodal( int entity, double* T, double* RhoMin, double* RhoMax, double* PMin, double* PMax )
{
  using namespace NSP_FEOS_LIB;
  char routinename[STRSIZE] = "FEOS_Get_Spinodal";
  int i;

  if(!Check_Maxwell_Init(entity, routinename)) exit(0);

  for(i=0; i<(*Critical[entity-1]).data.Niso; i++) {
    T[i] = (*Critical[entity-1]).data.Tiso[i];
    RhoMin[i] = (*Critical[entity-1]).data.Rhomin[i];
    RhoMax[i] = (*Critical[entity-1]).data.Rhomax[i];
    PMin[i] = (*Critical[entity-1]).data.Pmin[i];
    PMax[i] = (*Critical[entity-1]).data.Pmax[i];
  }

  if(PrintFlag) printf("\n<=> Spinodal of material entity %d successfully passed.\n", entity);
  return;  
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Get_EOS_All( int entity, int Maxwell, double Rho, double T, int* belowbinodal,
			      double* p, double* e, double* s, double* f, double* q, double* qtot,
            double* pe, double* ee, double* se, double* fe, 
            double* pi, double* ei, double* si, double* fi,
            double* pTF, double* eTF, double* sTF, double* fTF )
{ 
  using namespace NSP_FEOS_LIB;
  char routinename[STRSIZE] = "FEOS_Get_EOS_All";

  if(Maxwell) {
    if(!Check_Maxwell_Init(entity, routinename)) exit(0);
  }
  else {
    if(!Check_Mat_Init(entity, routinename)) exit(0); 
  }
  
  GetAllMaxwellEOSQuantities( ionpart[entity-1], qipscheme[entity-1], Critical[entity-1], 0, Maxwell, 
		 	 Rho, T, belowbinodal, p, e, s, f, q, qtot, pe, ee, se, fe, pi, ei, si, fi, pTF, eTF, sTF, fTF );     
  return;
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Get_EOS( int entity, int task, int Maxwell, double Rho, double T, int* belowbinodal,
			                          double* p, double* e, double* s, double* f, double* q, double* qtot )
{
  using namespace NSP_FEOS_LIB;
  char routinename[STRSIZE] = "FEOS_Get_EOS";
  double p1, e1, s1, f1, p2, e2, s2, f2, p3, e3, s3, f3; 
  
  if(Maxwell) {
    if(!Check_Maxwell_Init(entity, routinename)) exit(0);
  }
  else {
    if(!Check_Mat_Init(entity, routinename)) exit(0);
  }

  switch(task) {
    case 1:  GetAllMaxwellEOSQuantities( ionpart[entity-1], qipscheme[entity-1], Critical[entity-1], 1, Maxwell, Rho, T, 
		 	                        belowbinodal, &p1, &e1, &s1, &f1, q, qtot, &p2, &e2, &s2, &f2, p, e, s, f, &p3, &e3, &s3, &f3 );
    case 2:  GetAllMaxwellEOSQuantities( ionpart[entity-1], qipscheme[entity-1], Critical[entity-1], 2, Maxwell, Rho, T, 
		 	                        belowbinodal, &p1, &e1, &s1, &f1, q, qtot, p, e, s, f, &p2, &e2, &s2, &f2, &p3, &e3, &s3, &f3 );
    case 3:  GetAllMaxwellEOSQuantities( ionpart[entity-1], qipscheme[entity-1], Critical[entity-1], 3, Maxwell, Rho, T, 
		 	                        belowbinodal, &p1, &e1, &s1, &f1, q, qtot, &p2, &e2, &s2, &f2, &p3, &e3, &s3, &f3, p, e, s, f );
    default:  GetAllMaxwellEOSQuantities( ionpart[entity-1], qipscheme[entity-1], Critical[entity-1], 0, Maxwell, Rho, T, 
		 	                        belowbinodal, p, e, s, f, q, qtot, &p1, &e1, &s1, &f1, &p2, &e2, &s2, &f2, &p3, &e3, &s3, &f3 );
  } 

  return;
}

//////////////////////////////////////////////////////////////////

extern "C" void FEOS_Get_Pmin_Pmax( int entity, double T,
			      double* RhoMin, double* RhoMax, double* PMin, double* PMax )
{
  using namespace NSP_FEOS_LIB;
  char routinename[STRSIZE] = "FEOS_Get_Pmin_Pmax";

  if(!Check_Mat_Init(entity, routinename)) exit(0);

  if(!contains_loop(ionpart[entity-1], qipscheme[entity-1], T, T_ZERO)) {
    printf("\nLIB-ERROR in FEOS_Get_Pmax_Pmin ---> No loop on isotherm T = %.2e eV !!!\n", T); 
    exit(0);
  }

  getPmax_Pmin( ionpart[entity-1], qipscheme[entity-1], T, 
                PMax, RhoMax, PMin, RhoMin, 0 );
  return;
}

//////////////////////////////////////////////////////////////////
// eof.