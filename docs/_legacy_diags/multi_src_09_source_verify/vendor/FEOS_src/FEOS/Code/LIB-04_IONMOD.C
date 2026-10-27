//////////////////////////////////////////////////////////////////
// routines for reading the material parameter db and calculation of  
// the ionic EOS, the bonding correction, and the soft-sphere function 
// used by the FEOS library
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#include "LIB-04_IONMOD.H"

//////////////////////////////////////////////////////////////////

Ionpart::Ionpart( int matnumber, int maxwellflag, int softsphereflag, int printflag )
{
  // reads material parameters out of material database
  // all data (A[], Z[], X[], Rsolid, BM, ... ) in cgs units!
  
  readfile rf;
  int i;
  char matsection[STRSIZE], matprefix[STRSIZE], keyword[STRSIZE];

  MaterialNumber = matnumber;
  MaxwellFlag  = maxwellflag;
  SoftSphereFlag = softsphereflag;
  PrintFlag = printflag;

  sprintf(matsection,"%s%d%s","Material-",MaterialNumber,":" );
  sprintf(matprefix,"[%d]_",MaterialNumber ); 
  if(PrintFlag) printf( "  Read parameters for material %d from database:\n",MaterialNumber );
  rf.openinput((char*)MATERIAL_DATABASE_PATH);

  sprintf(keyword,"%s%s",matprefix,"SESAME-Number" ); 
  SESAMEnumber = atoi( rf.setget((char*)matsection,(char*)keyword) );
  if(PrintFlag) printf( "   SESAME-Number: %d\n", SESAMEnumber);	
  sprintf(keyword,"%s%s",matprefix,"Treference" ); 
	T_standard = atof( rf.setget((char*)matsection,(char*)keyword) );
  if(PrintFlag) printf( "   Reference temperature: %e eV\n", T_standard);	
  sprintf(keyword,"%s%s",matprefix,"Rhoreference" ); 
	rhosolid = atof( rf.setget((char*)matsection,(char*)keyword) );
  if(PrintFlag) printf( "   Reference density: %e g/cm^3\n", rhosolid);
  sprintf(keyword,"%s%s",matprefix,"Bulk-Modulus" ); 
	BulkModulus = atof( rf.setget((char*)matsection,(char*)keyword) );
  if(PrintFlag) printf( "   Bulk modulus: %e dyne/cm^2\n", BulkModulus);
  sprintf(keyword,"%s%s",matprefix,"Number-of-Elements" ); 
  Nelements = atoi( rf.setget((char*)matsection,(char*)keyword) );
  if(PrintFlag) printf( "   Number of elements: %d\n", Nelements);
  
  // get SoftSphere-Data
  if(SoftSphereFlag) {
    sprintf(keyword,"%s%s",matprefix,"Ecohesive" ); 
	  E_cohesive = atof( rf.setget((char*)matsection,(char*)keyword) );
	  if(PrintFlag) printf( "   Cohesive energy / enthalpy of sublimation: %e erg/g\n", E_cohesive);
    sprintf(keyword,"%s%s",matprefix,"Soft-Sphere-m" ); 
	  softsphere_m = atof( rf.setget((char*)matsection,(char*)keyword) );
    sprintf(keyword,"%s%s",matprefix,"Soft-Sphere-n" ); 
	  softsphere_n = atof( rf.setget((char*)matsection,(char*)keyword) );
	  if(PrintFlag) printf( "   Soft-sphere function parameters: m = %f, n = %f\n", softsphere_m, softsphere_n);
  }
  else E_cohesive = softsphere_m = softsphere_n = softsphere_A = softsphere_B = 0.0;

  // allocate memory for Aelement, Zelement, Xelement_tot and Xelement
  if(Nelements>0) {
  	Aelement = dvector(0,Nelements-1);
  	Zelement = dvector(0,Nelements-1);
  	Xelement_tot = dvector(0,Nelements-1);
  	Xelement_frac = dvector(0,Nelements-1);
	  for(i=0; i<Nelements; i++) {
		  Aelement[i] = 0.0;
		  Zelement[i] = 0.0;
		  Xelement_tot[i] = 0.0;
		  Xelement_frac[i] = 0.0;
	  }
  }
  else {
	  printf("\nLIB-ERROR in Ionpart::Ionpart ---> Number of elements < 1 !!!\n");
  	rf.closeinput();
	  exit(0);
  }

  // get A, X and Z for all elements
  Xtot = 0.0;
  for(i=0; i<Nelements; i++) {
    sprintf(keyword,"%s%s%d%s",matprefix,"A[",i+1,"]" );
	  Aelement[i] = atof( rf.setget((char*)matsection,(char*)keyword) );
    sprintf(keyword,"%s%s%d%s",matprefix,"Z[",i+1,"]" );
	  Zelement[i] = atof( rf.setget((char*)matsection,(char*)keyword) );
    sprintf(keyword,"%s%s%d%s",matprefix,"X[",i+1,"]" );
	  Xelement_tot[i] = atof( rf.setget((char*)matsection,(char*)keyword) );
    if(PrintFlag) printf("   Element %d of %d: A = %f, Z = %f, X = %f\n", i+1, Nelements, Aelement[i], Zelement[i], Xelement_tot[i]);
		Xtot += Xelement_tot[i];
    if(Aelement[i]<=0.0 || Zelement[i]<=0.0 || Xelement_tot[i]<=0.0) {
	    printf("\nLIB-ERROR in Ionpart::Ionpart ---> Non-positive value of A, Z, or X for element %d !!!\n",i+1);
  	  rf.closeinput();
	    exit(-1);
    }      	  
  }

  rf.closeinput();
  if(PrintFlag) printf("  Done.\n");

  // calculate Xelement[] and mean / total values of Aelement[] and Zelement[]
  Amean = Zmean = Atot = Ztot = 0.0;
  for(i=0; i<Nelements; i++)
  {
	  Xelement_frac[i] = Xelement_tot[i] / Xtot;
	  Atot += Aelement[i] * Xelement_tot[i];
	  Ztot += Zelement[i] * Xelement_tot[i];
	  Amean += Aelement[i] * Xelement_frac[i];
	  Zmean += Zelement[i] * Xelement_frac[i];
  }

  if(Nelements>1 || Xelement_tot[0]!=1.0) {
    if(PrintFlag) printf("  Total (mean) value of A: %f (%f)\n", Atot, Amean);
    if(PrintFlag) printf("  Total (mean) value of Z: %f (%f)\n", Ztot, Zmean);
  }

  AmeanMp = Amean * M_proton;
  AtotMp  = Atot * M_proton;
  rref    = Amean / (9.0*pow( Zmean, 0.3 ) );
  b_cow   = 0.6 * pow( Zmean, EIN_NEUNTEL );    
  gamma_F = gamma_s = kTd = kTm = alpha = deriv_kTd_dr = b_bond = Eo_bond = E_zero = p0_bonding = p1_bonding = p2_bonding = f = df  = 0.0;
}

//////////////////////////////////////////////////////////////////

Ionpart::~Ionpart()
{
  free_dvector( Aelement,0,Nelements-1 );
  free_dvector( Zelement,0,Nelements-1 );
  free_dvector( Xelement_tot,0,Nelements-1 );
  free_dvector( Xelement_frac,0,Nelements-1 );      
}

//////////////////////////////////////////////////////////////////

void Ionpart::getEmpiricalModel( double rho )
{
  // rho [cgs]
  // kTm [eV] (melting Temp) 

  double xi,opxi;

  xi   = rho/rref;
  opxi = 1.0+xi;

  kTm = 0.32 * pow(xi,( 2.0*b_cow + ZEHN_DRITTEL )) 
    / (opxi*opxi*opxi*opxi);                    // eV

  kTd = ( 1.68 / (Zmean+22.0) ) * ( pow(xi, b_cow+2.0) / (opxi*opxi)); // eV

  gamma_s = b_cow + 2.0/opxi;
  
  alpha   = 0.0262* (pow(Amean, ZWEI_DRITTEL) / pow( Zmean, 0.2) ) * (Zmean+22.0)*(Zmean+22.0);
  
  gamma_F = (( 3.0 * b_cow - 1.0)*rho + (3.0 * b_cow + 5.0)*rref) / (rho+rref);

  deriv_kTd_dr = 1.68*(2. + b_cow)*pow(rho/rref,1. + b_cow)/(pow(1 + rho/rref,2)*rref*(22. + Zmean)) - 
    3.36*pow(rho/rref,2. + b_cow)/(pow(1 + rho/rref,3)*rref*(22. + Zmean));
  
  return;
}

//////////////////////////////////////////////////////////////////

void Ionpart::getIonicQuantities( double rho, double T,
			 double *P_i, double *Ei, double *Fi, double *Si )
{
  // ALWAYS get empirical model first !
  // rho [cgs]
  // T   [eV]   !!!
  // Pi  [cgs]
  // Ei  [cgs]
  // Fi  [cgs]
  // Si  [cgs]
  
  double u,w;
  //
  if(rho <= RHO_ZERO) rho = RHO_ZERO;  // set R to min value
  if(T <= T_ZERO) T = T_ZERO;          // set T to min value
  //
  // numerics get unstable after R0 = 1.0e-8 g/ccm, T0 = 1.0e-4 eV. 
  // this is equivalent to assuming limiting law T-> 0
  //
  getEmpiricalModel( rho ); 
  //
  //  to get values for: kTm kTd gamma_s alpha gamma_F deriv_kTd 
  //  these variables depend only upon density.
  //
  {
      u = kTd / T;
      w = kTm / T;
      if(w > 1.0) {                   // solid phase
	if(u >= 3.0) get_f_cold_solid( u ); 
	else get_f_hot_solid( u );
	
	*Fi  = eV2cgs*T * f/ AmeanMp;
	*P_i = eV2cgs* (rho * rho / AmeanMp) * df* deriv_kTd_dr;
	*Ei  = eV2cgs*kTd* df / AmeanMp;
	*Si  = (*Ei-(*Fi)) / T;
      }//solid phase
      else 
	{                         // liquid phase
	get_f_liquid(u,w);
	*Fi  = f * eV2cgs*T/AmeanMp;
	*P_i = rho*eV2cgs*T/ AmeanMp  * (1.0 + gamma_F *
				     pow(w , EIN_DRITTEL ) );
	*Ei  = 1.5* eV2cgs*T/ AmeanMp * (1.0 + 
				     pow( w, EIN_DRITTEL ));
	*Si  = (*Ei-(*Fi)) / T;
      }//liquid phase
  }
  return;
}

//////////////////////////////////////////////////////////////////

void Ionpart::getBondingParameters( double pe_solid, double dpedr_solid, double Ee_solid,
				    double pe_zero, double Ee_zero )
{ 
  // pe & dpdr in cgs, from QIPscheme;
  // bonding parameters in cgs units

  double 
    pi_solid,dpidr_solid,
    Ei_solid,fi,si,p2,e2,f2,s2,p0,E0;
  if(PrintFlag) printf("\n Calculate bonding contribution parameters:\n");

  // ionic pressure for standard conditions:

  getIonicQuantities( rhosolid, T_standard , 
		      &pi_solid, &Ei_solid, &fi, &si );
  getIonicQuantities( rhosolid*1.001, T_standard , 
		      &p2, &e2, &f2, &s2 );
  //
  dpidr_solid = (p2-pi_solid)/(0.001*rhosolid);
  //
  // for usual T_standard the agreement with the analytical expression for      
  // dpidr_solid is better than .5%
  //
  b_bond  = -2.0 + 3.0 * ( rhosolid * 
			   (dpedr_solid + dpidr_solid) 
			   - BulkModulus )/(pe_solid+pi_solid);
  Eo_bond = 3.0*(pe_solid+pi_solid)/(b_bond*rhosolid);
  if(PrintFlag) printf("  E0 = %e erg/g\n  b = %e\n Done.\n", Eo_bond , b_bond );

  if(PrintFlag) printf("\n Calculate energy offsets:\n");
    Ei_Offset = Ei_solid;  // set energy zero at standard conditions (R_solid,T_standard)
    Ee_Offset = Ee_solid;
  if(PrintFlag) printf("  Ei_Offset = %+e erg/g\n  Ee_Offset = %+e erg/g\n Done.\n", Ei_Offset, Ee_Offset);
    
  if(SoftSphereFlag) {
    if(PrintFlag) printf( "\n Calculate soft sphere function parameters:\n" );
	  p0 = pe_zero - pe_solid - pi_solid;
	  E0 = Ee_zero - Ee_solid - Ei_solid;
	  softsphere_A = ( E0 - E_cohesive - ( p0 / ( softsphere_m * rhosolid ) ) ) 
		       / ( pow( rhosolid, softsphere_n ) * ( 1 - ( softsphere_n / softsphere_m ) ) );
	  softsphere_B = ( softsphere_A * pow( rhosolid, softsphere_n - softsphere_m ) * softsphere_n / softsphere_m )
		       - ( p0 / ( softsphere_m * pow( rhosolid, softsphere_m + 1 ) ) );
	  if(PrintFlag) printf("  A = %e erg*cm^(3n)/g^(n+1)\n  B = %e erg*cm^(3m)/g^(m+1)\n Done.\n", softsphere_A, softsphere_B);
  }
  return;
}

//////////////////////////////////////////////////////////////////

void Ionpart::get_f_cold_solid( double u )
{
  // Cowan Model
  // u dim.less
  double u_2 = u*u,
    u_3 = u_2*u,
    u_4 = u_3*u,
    eu = exp(u);
  if (u<ZERO) {
    printf("\nLIB-ERROR in Ionpart::get_f_cold_solid !!!\n");
    exit(0);
  }
  if ( u < 50.0) {
    f = 3.0 * (1.0 + 6.0/u_3 + 6.0/u_2 + 3.0/u) / eu - 
      pi4 / (5.0*u_3) + NEUN_ACHTEL*u + 3.0*log(1.0 - exp(-u) );
    df = NEUN_ACHTEL - 3.0/eu + 3.0/(-1.0 + eu) - 54.0/( eu*u_4) + 
      3.0*pi4 / (5.0*u_4) - 54.0/( eu*u_3) - 
      27.0/( eu*u_2) - 9.0/(eu*u );
  }
  else {
    f  = NEUN_ACHTEL*u;
    df = NEUN_ACHTEL;
  }
  // cout << "get_f_cold_solid: " << u << " " << eu << " " << f << " " << df << "\n" << flush;
  return;
}

//////////////////////////////////////////////////////////////////

void Ionpart::get_f_hot_solid( double u)
{ 
  // Cowan Model
  // u dim.less
  
  double u_2 = u*u,
     u_3 = u_2 * u,
     u_4 = u_3 * u;
  if (u<ZERO) {
   printf("\nLIB-ERROR in Ionpart::get_f_hot_solid !!!\n");
    exit(0);
  }
   // the 6th power is omitted, as it worsens the result;
   f  = -1.0 + 3.0*u_2/40.0 - u_4 / 2240.0 + 3.0*log(u);
   df = 3.0/u + 3.0*u/20.0 - u_3 / 560.0;         
   return;
}

//////////////////////////////////////////////////////////////////

void Ionpart::get_f_liquid(double u, double w)
{ 
  // Cowan Model
  // u dim.less
  
  f = -5.5 + 4.5 * pow( w, EIN_DRITTEL) + 1.5 * log(u*u / w);
  return;
} 

//////////////////////////////////////////////////////////////////

void Ionpart::get_bonding_contrib( double rho, double* P, double* E) 
{
  // bonding contrib in cgs units
  
  double  e;
  if(rho <= RHO_ZERO) rho = RHO_ZERO;
  e = exp( b_bond* (1.0 - pow( rhosolid/rho, EIN_DRITTEL)) );
  (*E) =  Eo_bond*( 1.0 - e );
  (*P) = -(Eo_bond*b_bond*rhosolid/3.0)* e * pow( rho/rhosolid, ZWEI_DRITTEL );
  return;
}

//////////////////////////////////////////////////////////////////

void Ionpart::getSoftSphereQuantities( double rho, double* P, double* E) 
{
  // soft sphere quantities in cgs units
  
  if(rho <= RHO_ZERO) rho = RHO_ZERO;
  (*E) = ( softsphere_A * pow( rho, softsphere_n ) ) - ( softsphere_B * pow( rho, softsphere_m ) ) + E_cohesive + Ei_Offset + Ee_Offset;
  (*P) = ( softsphere_A * softsphere_n * pow( rho, softsphere_n + 1 ) ) - ( softsphere_B * softsphere_m * pow( rho, softsphere_m + 1 ) );
  return;
}

//////////////////////////////////////////////////////////////////
// eof.