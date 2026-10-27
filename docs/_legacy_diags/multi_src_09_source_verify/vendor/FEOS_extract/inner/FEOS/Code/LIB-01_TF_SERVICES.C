//////////////////////////////////////////////////////////////////
// service routines for (1) reading the TF-table file and
// (2) fast computation of the Fermi-Dirac function 
//     (F 1/2 and F 3/2) and its inverse function F^-1
// used by the FEOS library
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#include "LIB-01_TF_SERVICES.H"

//////////////////////////////////////////////////////////////////

void get_memory( TFtable* table, int NR, int NT, int printflag )
{
  // get memory for TF table;
  // TF table counters start from 1 !
  
  if(printflag) printf("   Allocate memory for Thomas-Fermi table...");
  (*table).NR = NR;
  (*table).NT = NT;
  // allocate memory:
  (*table).rho = dvector(1,NR);
  (*table).Te  = dvector(1,NT );
  
  (*table).Pe = dmatrix(1,NR,1,NT );
  (*table).Ee = dmatrix(1,NR,1,NT ); 
  (*table).Se = dmatrix(1,NR,1,NT ); 
  (*table).Fe = dmatrix(1,NR,1,NT );
  
  (*table).Q      = dmatrix(1,NR,1,NT ); 
  (*table).dPdT   = dmatrix(1,NR,1,NT );
  (*table).Virial = dmatrix(1,NR,1,NT );
  (*table).Nernst = dmatrix(1,NR,1,NT );
  if(printflag) printf(" done.\n");
  return;
}

//////////////////////////////////////////////////////////////////

void write_TF_TABLE( char* name_in, TFtable* table, int printflag )
{
  // format: see at read..
  
  int i,j,
    NR = (*table).NR,
    NT = (*table).NT;
  FILE* h;
  if(printflag) printf("\nWrite Thomas-Fermi table to file ");
  if(printflag) printf("%s\n",name_in);
  h = fopen( name_in, "w" );

  for( i = 1; i<=NR; i++ ) {
    fprintf( h, "%.15e\n", (*table).rho[i] );
    for( j = 1; j<=NT; j++ ) 
      fprintf(h,"%.15e  %.15e  %.15e  %.15e  %.15e  %.15e\n",
	      (*table).Te[j],
	      (*table).Pe[i][j] ,
	      (*table).Ee[i][j], 
	      (*table).Fe[i][j],
	      (*table).Q[i][j],
	      (*table).dPdT[i][j] );
	      }
  fclose( h);
  if(printflag) printf( "Wrote condensed TF table (no control data)\n");
  return;
}

//////////////////////////////////////////////////////////////////

void clear_TF_TABLE( TFtable* table )
{
  int NR = (*table).NR, NT = (*table).NT;
  // clear memory:
  free_dvector( (*table).rho, 1,NR);
  free_dvector( (*table).Te, 1, NT);
  delete_dmatrix( (*table).Pe, 1,NR,1,NT );
  delete_dmatrix( (*table).Ee, 1,NR,1,NT );
  delete_dmatrix( (*table).Se, 1,NR,1,NT );
  delete_dmatrix( (*table).Q,  1,NR,1,NT );
  delete_dmatrix( (*table).dPdT,   1,NR,1,NT ); 
  delete_dmatrix( (*table).Virial, 1,NR,1,NT );
  delete_dmatrix( (*table).Nernst, 1,NR,1,NT );
  return;
}

//////////////////////////////////////////////////////////////////

void read_TF_TABLE( char* name_in, TFtable* table, int printflag )
{
  // format of the TF table (units: cgs, T[eV], mass density)
  // scaling CAN be done already here.
  //
  // indices from (1,1) .. ( NR,  NT)
  // R(i)
  // T(j)  Pe(i,j)  Ee(i,j)  Fe(i,j)  Q(i,j)  dP/dT(i,j)
  // T(j+1) ....  
  // R(i+1)
  // T(j)...

  int i,j,NR,NT;
  double r1,r2,t1,t2;
  char **argv;
  int argc;
  readfile rf;

  argv = rf.cmatrix( MAX_LINE_NO , MAX_LINE_LENGTH ); 
  if(printflag) printf("\n  Read Thomas-Fermi table:\n");
  if(printflag) printf("   Source: %s\n",name_in);
  rf.openinput( name_in );
  // get table size:
  if( rf.getTableSize( &NR,&NT )!=0 ) { 
    printf("\nLIB-ERROR in read_TF_TABLE ---> Error in file %s !!!\n",name_in);
    exit(0);
  }

  get_memory( table, NR, NT, printflag );

  // skip comment lines:
  do { rf.read_line( &argc, argv ); }
  while( strcmp( argv[0],"#") == 0 );

  // read Table:  
  for(i=1;i<=NR;i++) {  
     if( i>1 ) rf.read_line( &argc, argv );
     if(argc!=1) {
       printf("\nLIB-ERROR in read_TF_TABLE ---> %d !!!\n",argc); 
       exit(0); 
     } 
     (*table).rho[i] = atof( argv[0] );
     for(j=1;j<= NT;j++) { 
       rf.read_line( &argc, argv );
       if( argc != WORDS_IN_TF_LINE ) { 
	 printf("\nLIB-ERROR in read_TF_TABLE ---> Wrong number of words in TF-table line !!!\n");
	 exit(0); 
       }
       (*table).Te[j]     = atof( argv[0] );
       
       (*table).Pe[i][j]  = atof( argv[1] );
       (*table).Ee[i][j]  = atof( argv[2] );
       (*table).Fe[i][j]  = atof( argv[3] );

       (*table).Se[i][j]  = ( (*table).Te[j] > ZERO ) ? 
       	 ( (*table).Ee[i][j] - (*table).Fe[i][j]) / 
	 ( eV2cgs*(*table).Te[j] ) : 0.0;
       
       (*table).Q[i][j]   = atof( argv[4] );
       (*table).dPdT[i][j]    = atof( argv[5] );
     }
   }
  rf.free_cmatrix( argv );
  rf.closeinput();
  r1 = (*table).rho[1]; 
  r2 = (*table).rho[NR];
  t1 = (NT==1) ? 0.0 : (*table).Te[1];
  t2 = (NT==1) ? 0.0 : (*table).Te[NT];
  if(printflag) printf("   Table size (densities x temperatures): %d x %d\n", NR, NT);
  if(printflag) printf("   Table boundaries (density, temperature):\n");
  if(printflag) printf("    (%e g/cm^3, %e eV) ...\n", r1, t1);
  if(printflag) printf("    ... (%e g/cm^3, %e eV)\n", r2, t2);
  if(printflag) printf("  Done.\n");
  return;
}

//////////////////////////////////////////////////////////////////
// Sommerfeld Expansionen fuer die Fermi Integrale F 1/2 und F 3/2:
//////////////////////////////////////////////////////////////////
// zu F 3/2: 
// ueberarbeitet am 21.4 und ueberprueft am 21.4.97 .. letzte Verbesserungen am 1.5.97 (s.P28)
// die mathematica Naeherungen sind gespeichert im File mathematica/ Fermi32C_m1.tex und anderen
// die Integrationen fuer x>2.5 mussten teilweise mit endlicher oberer Grenze 
// ausgefuehrt werden, die wurde aber dann noch einmal verdoppelt um Konvergenz zu testen
// vergleich mit fermi_th ergibt eine globale max relative abweichung von 2e-8 im bereich x=12, sonst liegt sie
// deutlich unter 1e-8.
//////////////////////////////////////////////////////////////////
// zu F 1/2: 
// ueberarbeitet am 1.5.97 (s. P29 )
//////////////////////////////////////////////////////////////////

double quickfermi_oh( double x)
{    
  // die Approximation von Latter sind bloss auf 4 stellen genau; eigene app;

  double x_2 = x*x,
    x_3 = x*x*x,
    x_4 = x_3*x,
    x_5 = x_4*x,
    x_6 = x_5*x,
    x_7 = x_6*x,
    x_8 = x_6*x*x,
    x_9 = x_8*x,
    x_10 = x_4*x_6;
  if( x >= 1e5 ) return (2.0/3.0) * x * sqrt(x);
  else if( x >= 13.0 ) return (2.0/3.0) * x * sqrt(x) * ( 1.0 + 1.2337005 / (x*x) + 
							  1.0654119/x_4 + 9.7015185/x_6 + 
						       242.71502/x_8 + 12313.691/x_10);
  else if( x > 8.0 ) return 0.7410987199660504 + 0.3761318377118113*x + 0.2872992438061027*x_2 - 
		     0.02226374955497967*x_3 + 0.001692354431607977*x_4 - 
		     0.000091830566339613*x_5 + 3.216939384343134e-6*x_6 - 
		     6.239076800137418e-8*x_7 + 3.865051228160352e-10*x_8 + 
		     3.70969885900951e-12*x_9; // mathematica x = 10
		     
  else if( x >= 4.5 ) return 0.7853093566519505 + 0.3780659704865604*x + 0.2640576757236753*x_2 - 
			0.00967712755589787*x_3 - 0.00168179321970783*x_4 + 
			0.0004531617663106636*x_5 - 0.00005260160627769095*x_6 + 
			3.513657119917058e-6*x_7 - 1.312075827508539e-7*x_8 + 
			2.13748016744273e-9*x_9; // mathematica Fermi12C_15.tex x = 6.5
  else if( x > 2.2 ) return 0.6722709193775787 + 0.5541626445907743*x + 0.1436239832847793*x_2 + 
		     0.03699298804672579*x_3 - 0.01258227710471903*x_4 + 
		     0.001901797995484187*x_5 - 0.0001218660202322661*x_6 - 
		     4.822513212695542e-6*x_7 + 1.282653875502436e-6*x_8 - 
		     6.100798921844706e-8*x_9;// mathmeatica x = 3.2

  else if( x > 0.75 ) return 0.6781202720104681 + 0.5359017815743759*x + 0.1689540096107734*x_2 + 
		     0.01660850150751696*x_3 - 0.002195424894747387*x_4 - 
		     0.001507002087946002*x_5 + 0.0005681056697179386*x_6 - 
		     0.00007790044888034985*x_7 + 2.699337947708683e-6*x_8 + 
		     2.388084293425615e-7*x_9;// mathematica Fermi12C_15.tex x = 1.5
  else if( x > -0.5 ) return 0.6780938951543054 + 0.5360774649713175*x + 0.1684295597145664*x_2 + 
		      0.01752969720632666*x_3 - 0.003243632130392803*x_4 - 
		      0.0007093307243235336*x_5 + 0.000168389610836477*x_6 + 
		      0.00004215847921983807*x_7 - 0.00001128040886011779*x_8 - 
		      1.998912234285311e-6*x_9;// mathematica x=0.1
  else if( x>= -0.75 ) return 0.6780938957520019 + 0.5360774756028173*x + 0.1684296507096877*x*x + 
		      0.0175301642671074*x_3 - 0.003242074198566068*x_4 - 
		      0.0007058471045710635*x_5 + 0.0001736139228957568*x_6 + 
		      0.00004692644385449142*x_7 - 8.58291804420165e-6*x_8 - 
		      3.112875068364535e-6*x_9;// mathematica Fermi12C_m05.tex
  else if( x>=-1.5 ) return 0.6780945914711093 + 0.5360844954190838*x + 0.1684615148877975*x*x + 
		     0.01761575804115024*x_3 - 0.003091722295138215*x_4 - 
		     0.0005261876980642036*x_5 + 0.0003201593541047041*x_6 + 
		     0.0001258980810319536*x_7 + 0.00001702001369767442*x_8 + 
		     7.034182195883288e-7*x_9;// mathematica Fermi12C_m0.5.tex at x = -1.0
  else if( x > -2.5) return 0.6778750800456719 + 0.5350193042441479*x + 0.166165235081562*x*x + 
			0.01473814348154787*x_3 - 0.005389513666863979*x_4 - 
			0.001726723645886422*x_5 - 0.0000824233276219026*x_6 + 
			0.00004586780311295133*x_7 + 9.48194693953914e-6*x_8 + 
		       6.027045989816111e-7*x_9;// mathmatica Fermi12C_m2.tex 

  else if( x<=-2.5) {
   double  ex1 = exp(x),
     ex2 = exp(2.0*x), ex3 = exp(3.0*x), ex4 = exp(4.0*x),
     ex5 = exp(5.0*x), ex6 = exp(6.0*x),
     a=pow(2.0,1.5),b=pow(3.0,1.5),c=pow(4.0,1.5),
     d=pow(5.0,1.5),e=pow(6.0,1.5),f=pow(7.0,1.5);
   return ( (sqrt(Pi)/2.0) * ex1 * (1.0 - ex1/a + ex2/b - ex3/c + 
				     ex4/d - ex5/e + ex6/f)); 
  }
  printf("\nLIB-ERROR in quickfermi_oh ---> no condition fulfilled at x = %e !!!\n", x);
  return(0);
}

//////////////////////////////////////////////////////////////////

double quickfermi_th( double x)
{        
  double x_2 = x*x,
    x_3 = x*x*x,
    x_4 = x_3*x,
    x_5 = x_2*x_3,
    x_6 = x_5*x,
    x_7 = x_6*x,
    x_8 = x_4*x_4,
    x_9 = x_8*x,
  // x_10 = x_4*x_6,
    tt_fac = 1.5*(sqrt(Pi)/2.0); // (3/2)!
  if( x >= 1e6 ) return (2.0/5.0) * x*x * sqrt(x);

  else if( x >= 12.5 ){ // this part is from Zittel:   
    double a = (5.0/2.0)*(3.0/2.0),
      b = a/4.0,
      c = b*(15.0/4.0),
      d = c*(63.0/4.0),
      ps = Pi*Pi, pf = ps*ps, px = ps*pf, pe = pf*pf;  // powers of Pi
      
    return (2.0/5.0) * x*x * sqrt(x) * ( 1.0 + ps*a/ (6.0 * x*x) 
					 - b * pf* 7.0/(4.0*90.0*x_4)
					 - c * px* 31.0/(945.0*16.0*x_6)
					 - d * pe* 127.0/(604.0*800.0*x_8) );
					 
  } else if( x >= 10.0 ) return -1.493355463914696 + 3.463808970369304*x - 0.6386880362031782*x*x + 
			   0.3538599529655456*x_3 - 0.03918969055576082*x_4 + 
			   0.00352321929632565*x_5 - 0.0002194725926562693*x_6 + 
			   8.92269605659624e-6*x_7 - 2.131757821242969e-7*x_8 + 
			   2.272463301097573e-9*x_9;// mathematica Fermi32C_10.tex
  else if( x >= 9.0 ) return 5.024813526645957 - 2.649618485756767*x + 1.914917074070413*x_2 - 
		       0.2695320860550371*x_3 + 0.05881120189759744*x_4 - 
		       0.006763458130217418*x_5 + 0.0005013244265139806*x_6 - 
		       0.00002358313782838606*x_7 + 6.427371990987753*1.0e-7*x_8 - 
		       7.751063411667986*1.0e-9*x_9;// mathemmatica Fermi32C_2.5
  else if( x >= 5.0 ) return 0.991489118148927 + 1.275089201273139*x + 0.2193696414211994*x_2 + 
			0.1571919508074917*x_3 - 0.0101109751485369*x_4 + 
			0.0006417306558978641*x_5 - 0.00002762192668166454*x_6 + 
			6.180373592069602*1.0e-7*x_7 - 1.485863961941658*1.0e-10*x_8 - 
			2.08048989915609*1.0e-10*x_9;// mathemmatica Fermi32C_2.5
  else if( x >= 4.0 ) return 1.117064969214628 + 1.083588047585655*x + 0.3502710152841245*x_2 + 
			0.1045586119431793*x_3 + 0.003605133988387117*x_4 - 
			0.001760073192012786*x_5 + 0.0002548988763324562*x_6 - 
			0.00002090133038103599*x_7 + 9.62615046890111*1.0e-7*x_8 - 
			1.947693505685285*1.0e-8*x_9;// mathemmatica Fermi32C_2.5
  else if( x >= 2.5 ) return 1.155596353799876 + 1.007420879457727*x + 0.4172608223265338*x_2 + 
			0.07021860868180835*x_3 + 0.01487815608412203*x_4 - 
			0.004206230063343634*x_5 + 0.0006031020742433344*x_6 - 
			0.00005184853260225925*x_7 + 2.482646238943474*1.0e-6*x_8 - 
			4.918014743785185*1.0e-8*x_9;  // mathemmatica Fermi32C_2.5
  else if( x >= 0.8 ) return 1.152796383758663 + 1.017194178697429*x + 0.401885024183938*x_2 + 
			0.084550448518415*x_3 + 0.006142503571054542*x_4 - 
			0.000590079730245578*x_5 - 0.0004148326789706484*x_6 + 
			0.0001362444485530116*x_7 - 0.00001823322174197249*x_8 + 
			9.87207481471179*1.0e-7*x_9;  // mathematica Fermi32C_1.5.tex: finite integrals
  else if( x >= -0.5 ) return 1.152803836037439 + 1.017140838839635*x + 0.4020580986474062*x*x + 
			0.0842147801768608*x_3 + 0.006573636512956382*x_4 - 
			0.000973090395750465*x_5 - 0.000177326384456917*x_6 + 
			0.00003604750764336683*x_7 + 8.03964141857867*1.0e-6*x_8 - 
			2.179904978650983e-6*x_9;  // mathematica : Fermi32C_0.tex

  else if( x >=-1.5 ) return 1.152803823718153 + 1.017140830222122*x + 0.4020586229115065*x*x + 
			0.0842180959849742*x_3 + 0.006583751602159469*x_4 - 
			0.000954105899091371*x_5 - 0.0001537045988677822*x_6 + 
			0.00005594404792510411*x_7 + 0.0000188578172230503*x_8 + 
			1.781541621403099*1.0e-6*x_9;  // mathematica: Fermi32C_m1.tex
  else if(x >= -2.0 ) return 1.152789479875557 + 1.017046642918538*x + 0.401781937975338*x*x + 
			0.0837405547895698*x_3 + 0.006049727143728748*x_4 - 
			0.001355656020657105*x_5 - 0.000356874410005441*x_6 - 
			0.00001080287625043323*x_7 + 5.929366144796698e-6*x_8 + 
			6.559962777261008e-7*x_9;  // mathematica : Fermi32C_m15.tex
  else if( x<=-2.0) { // this part is from Zittel:   
   double  ex1 = exp(x),
     ex2 = exp(2.0*x), ex3 = exp(3.0*x), ex4 = exp(4.0*x),
     ex5 = exp(5.0*x), ex6 = exp(6.0*x),
     a=pow(2.0,2.5),b=pow(3.0,2.5),c=pow(4.0,2.5),
     d=pow(5.0,2.5),e=pow(6.0,2.5),f=pow(7.0,2.5);

   return ex1 *tt_fac* (1.0 - ex1/a + ex2/b - ex3/c 
		 + ex4/d - ex5/e + ex6/f); 
  }
  printf("\nLIB-ERROR in quickfermi_th ---> no condition fulfilled at x = %e !!!\n", x);
  return(0);
}

//////////////////////////////////////////////////////////////////

double fermi_1( int n, double p )
{
  // get inverse of Fermi function via Newton rootfinder

  double 
    eps_f_1 = 1.0e-4;
  double x,
    xstart = 1.0,
    delta,
    f,dx,df;
  x = xstart;
  if( n==1 ) {// for  F1/2 -1 
    if (p>2.0E7) return pow(1.5*p,0.6666);
    do 
      {
	f  = quickfermi_oh( x ) - p;
	df = (quickfermi_oh( 1.01*x ) - p - f)/(0.01*x);
	dx = f/df;
	x = x - dx;
      } 
    while( fabs(dx) > eps_f_1 );
    return x; 
  }
  else if( n==3) // for (F3/2) -1
    {
      if (p>1.0E12) return pow(2.5*p, 0.4);
      do {
	f = quickfermi_th( x ) - p;
	delta = 0.01;
	do {
	  df = (quickfermi_th( (1.0+delta)*x ) - p - f)/(delta*x);
	  delta *= 2.0;
	  if (delta>100.) {
      printf("\nLIB-ERROR in fermi_1 ---> p = %e f = %e, x = %e, q(x) = %e !!!\n",p,f,x,quickfermi_th( x ) ); 
	    exit(0);
	  }
	}
	while ( fabs(df) < ZERO ); // find good derivative ( df > ZERO )
	dx = f/df;
	x = x - dx;
      } 
      while( fabs(dx) > eps_f_1 );
      if (!( (x>0) || (x<0)) ) 	printf( "fermi_1: x = %e dx = %e f = %e df = %e\n",	x,dx,f,df);
      return x;
    }
  printf("\nLIB-ERROR in fermi_1 ---> wrong argument in inverse Fermi function !!!\n" ); 
  exit(0);
  return 0.0;
} 

//////////////////////////////////////////////////////////////////
// eof.