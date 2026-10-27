//////////////////////////////////////////////////////////////////
// routines for calculation of the single element Thomas-Fermi EOS
// part 1 of 2
// used by the FEOS library
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#include "LIB-02_TF_TABLE.H"

//////////////////////////////////////////////////////////////////

#define NO_PO_INTERPOL   // NO Printout: (where is interpolation routine now ?)

//////////////////////////////////////////////////////////////////

QIPscheme::QIPscheme( char* name_in, double A_in, double Z_in, int printflag ):ht( name_in, printflag )
{
  int i,j;
  PrintFlag = printflag;
  if(PrintFlag) printf("  Initialize QEOS interpolation scheme...");
  interested_in_Q = 1;
  //   printf( "check if matrix matches with table\n" );
  if( fabs( ht.TabMult_rho - QIPmult_rho ) > 1e-10 || 
      fabs( ht.TabMult_T - QIPmult_T ) > 1e-10 ) {
    printf("\nLIB-ERROR in QIPscheme::QIPscheme ---> Table does not match with interpolation matrix !!!\n");
    exit(0);
  }
  matextra_u0 = dmatrix( 0,7,0,7 );  
  matextra_t0 = dmatrix( 0,7,0,7 );  
  matextra_u_inf = dmatrix( 0,7,0,7 ); 
  matextra_t_inf = dmatrix( 0,7,0,7 );

  matextra_u0t0 = dmatrix( 0,3,0,3 );
  matextra_uinftinf = dmatrix( 0,3,0,3 );
  matextra_uinft0 = dmatrix( 0,3,0,3 );
  matextra_u0tinf = dmatrix( 0,3,0,3 );

  for( i=0;i<=7;i++ )
    for( j=0; j<=7;j++ )
      {
  matextra_u0[i][j]    = MATEXTRA_u0[i][j]; 
  matextra_u_inf[i][j] = MATEXTRA_u_inf[i][j];
  matextra_t0[i][j]    = MATEXTRA_t0[i][j];
  matextra_t_inf[i][j] = MATEXTRA_t_inf[i][j];
      }
   for( i=0;i<=3;i++ )
    for( j=0; j<=3;j++ )
      {
  matextra_u0t0[i][j]     = MATEXTRA_u0t0[i][j]; 
  matextra_uinftinf[i][j] = MATEXTRA_uinftinf[i][j];
  matextra_uinft0[i][j]   = MATEXTRA_uinft0[i][j];
  matextra_u0tinf[i][j]   = MATEXTRA_u0tinf[i][j];
      }
  u_field = ht.ufield;
  t_field = ht.Tfield;
  H   = ht.Hfield;
  H1  = ht.H1field;
  H2  = ht.H2field;
  H12 = ht.H12field;
  at_i = at_j = 1;      // store last position in table
  NU   = ht.NU;
  NT   = ht.NT;

  r_scal = 1.0/(A_in*Z_in);
  t_scal = 1.0/pow(Z_in,VIER_DRITTEL);
  p_scal = pow(Z_in,ZEHN_DRITTEL);
  e_scal = pow(Z_in,SIEBEN_DRITTEL)/A_in;
  s_scal = Z_in/A_in;
  q_scal = Z_in; 
  if(PrintFlag) printf(" done.\n");
}

//////////////////////////////////////////////////////////////////

double QIPscheme::getquantity( double r, double t, int choice )
{
  // all in cgs units
  double p,e,s,f,q;
  if(choice<5) {
    getTFquantities( r,t, &p,&e,&s,&f,&q );
    switch( choice ) {
    case 0 : return q;
    case 1 : return p;
    case 2 : return e;
    case 3 : return s;
    case 4 : return f;
    default : { printf( "\nLIB-ERROR in QIPscheme::getquantity ---> No quantity chosen !!!\n" ); exit(0); }
    }
  } else {
    Interpolate( pow(r,-ZWEI_DRITTEL ),t, &p,&e,&s );
    switch( choice ) {
    case 5 : return p;
    case 6 : return e;
    case 7 : return s;
    default : { printf( "\nLIB-ERROR in QIPscheme::getquantity ---> No quantity chosen !!!\n" ); exit(0); }
    }
  }
    return 0.0;
}

//////////////////////////////////////////////////////////////////
  
void QIPscheme::getTFquantities( double r, double t, 
				 double *P, double *E, 
				 double *S, double *F, 
				 double* Q )
{
  // r in  cgs units, t in eV as usual
  double u, 
     h, h1, h2;
  t *= eV2cgs;   // eV --> cgs
  r *= r_scal;
  t *= t_scal;   // scaling property of the TF - model !!

  u = pow( r, -ZWEI_DRITTEL );     

  Interpolate( u, t, &h, &h1, &h2 ); 

  *P =  p_scal * ZWEI_DRITTEL * pow( u, -2.5 ) * ( h-u*h1 );
  *E =  e_scal * ( (( h -  t * h2 ) / u ) );
  *S = -s_scal * eV2cgs * h2 / u;
  *F =  e_scal * ( (h/u));
  if (interested_in_Q) *Q =  q_scal * getQ( (*P)/p_scal, r,t,PrintFlag ); 
                                           // use unscaled pressure to obtain 
  else *Q = 0.0;                           // charge state, scale Q afterwards !
  return;
}

//////////////////////////////////////////////////////////////////

QIPscheme::~QIPscheme()
{
  delete_dmatrix( matextra_u0, 0,7,0,7 );
  delete_dmatrix( matextra_u_inf, 0,7,0,7 ); 
  delete_dmatrix( matextra_t0, 0,7,0,7 );
  delete_dmatrix( matextra_t_inf, 0,7,0,7 );

  delete_dmatrix( matextra_u0t0, 0,3,0,3 );
  delete_dmatrix( matextra_uinftinf, 0,3,0,3 );
  delete_dmatrix( matextra_uinft0, 0,3,0,3 );
  delete_dmatrix( matextra_u0tinf, 0,3,0,3 );
}

//////////////////////////////////////////////////////////////////

void QIPscheme::Interpolate(double u, double t, double *Y, double *Y1, double *Y2 )
{
  int i,j,a;
  a = shift_box( &at_i, &at_j, u_field,t_field, u,t, NU, NT );
  i = at_i;
  j = at_j;
#ifndef NO_PO_INTERPOL
  if(PrintFlag) printf( "Interpoliere fuer : %e[cgs] %e[eV]\n", pow(u,-1.5), t/eV2cgs );
#endif
  if( a == 0 ) {     // normal case  
    double y[5]   = { 0.0,H[i][j],H[i+1][j],H[i+1][j+1],H[i][j+1]         };
    double y1[5]  = { 0.0,H1[i][j],H1[i+1][j],H1[i+1][j+1],H1[i][j+1]     };
    double y2[5]  = { 0.0,H2[i][j],H2[i+1][j],H2[i+1][j+1],H2[i][j+1]     };
    double y12[5] = { 0.0,H12[i][j],H12[i+1][j],H12[i+1][j+1],H12[i][j+1] };
    
    Qbcuint( y,y1,y2,y12, 
	     u_field[i],u_field[i+1],t_field[j],t_field[j+1],
	     u,t, Y, Y1, Y2 );
    return;   
  } else 
  if( a == 1 ) {    // T --> 0
#ifndef NO_PO_INTERPOL
    if(PrintFlag) printf(" t -> 0\n");
#endif
    double y[3]   = { 0., H[i][j],H[i+1][j]     };
    double y1[3]  = { 0., H1[i][j],H1[i+1][j]   };
    double y2[3]  = { 0., H2[i][j],H2[i+1][j]   };
    double y12[3] = { 0., H12[i][j],H12[i+1][j] };
    Qextrapolate_t0( y,y1,y2,y12,
	      u_field[i],u_field[i+1],t_field[j],
	      u,t, Y, Y1, Y2 );
    return;
  } else 
    if( a == 2 ) {   // T --> oo 
#ifndef NO_PO_INTERPOL
   if(PrintFlag) printf( "t -> oo\n"); 
#endif
    double T = t/TSCALE;
    double   // interpolate shifted function:
      f   = 1.5*u*T*log(T),
      f1  = 1.5*  T*log(T),
      f2  = 1.5*u*(log(T)+1.0)/TSCALE,
      
      u1 = u_field[i],
      u2 = u_field[i+1],
      t2 = t_field[j]/TSCALE,
      tlogt = t2*log(t2),
      logtp1 = (log(t2)+1.0),

      g1 = 1.5*u1*tlogt,
      g2 = 1.5*u2*tlogt,
      g_1 = 1.5*tlogt,
      g_21 = 1.5*u1*logtp1/TSCALE,
      g_22 = 1.5*u2*logtp1/TSCALE,
      g_12 = 1.5*logtp1/TSCALE;

    double y[3]   = { 0., H[i][j]+g1,H[i+1][j]+g2         };
    double y1[3]  = { 0., H1[i][j]+g_1,H1[i+1][j]+g_1     };
    double y2[3]  = { 0., H2[i][j]+g_21,H2[i+1][j]+g_22   };
    double y12[3] = { 0., H12[i][j]+g_12,H12[i+1][j]+g_12 };
    Qextrapolate_t_inf( y,y1,y2,y12,
	      u_field[i],u_field[i+1],t_field[j],
	      u,t, Y, Y1, Y2 );

    (*Y)   -= f;
    (*Y1)  -= f1;
    (*Y2)  -= f2;
   
    return;
  }
  else  if( a == 3 ) {    // u --> 0
#ifndef NO_PO_INTERPOL
    if(PrintFlag) printf("u -> 0\n");
#endif
    double y[3]   = { 0., H[i][j]-Ho,H[i][j+1]-Ho };
    double y1[3]  = { 0., H1[i][j],H1[i][j+1]   };
    double y2[3]  = { 0., H2[i][j],H2[i][j+1]   };
    double y12[3] = { 0., H12[i][j],H12[i][j+1] };
    Qextrapolate_u0( y,y1,y2,y12,
          u_field[i],t_field[j],t_field[j+1],
          u,t, Y, Y1, Y2 );
    (*Y) += Ho;
    return;
  } 
  else  if( a == 4 ) {    // u --> oo
#ifndef NO_PO_INTERPOL
    if(PrintFlag) printf("u -> oo\n");
#endif
    double y[3]   = { 0., H[i][j],H[i][j+1]     };
    double y1[3]  = { 0., H1[i][j],H1[i][j+1]   };
    double y2[3]  = { 0., H2[i][j],H2[i][j+1]   };
    double y12[3] = { 0., H12[i][j],H12[i][j+1] };
    Qextrapolate_u_inf( y,y1,y2,y12,
		       u_field[i],t_field[j],t_field[j+1],
		       u,t, Y, Y1, Y2 );
    return;
  }

  /////////////////
  
    else if( a == 5 ) {  // u --> 0, t--> 0
#ifndef NO_PO_INTERPOL
      if(PrintFlag) printf("u-->0, t->0\n");
#endif      
      double 
  y   = H[i][j]-Ho,
  y1  = H1[i][j],
  y2  = H2[i][j],
  y12 = H12[i][j];
      Qextrapolate_u0t0(  &y,&y1,&y2,&y12,
           u_field[i],t_field[j],
           u,t, Y, Y1, Y2 ); 
      (*Y) += Ho; 
      return;
    }

  /////////////////

    else if( a == 6 ) { // u --> 0 , t --> oo 
#ifndef NO_PO_INTERPOL
      if(PrintFlag) printf(" u-> 0 t->oo\n");
#endif
      double T = t/TSCALE;
      double                       // interpolate shifted function:
  f   = 1.5*u*T*log(T),
  f1  = 1.5*  T*log(T),
  f2  = 1.5*u*(log(T)+1.0)/TSCALE,
  
  u1 = u_field[i],
  t2 = t_field[j]/TSCALE,
  tlogt = t2*log(t2),
  logtp1 = log(t2)+1.0,
  
  g = 1.5*u1*tlogt,
  g_1 = 1.5*tlogt,
  g_2 = 1.5*u1*logtp1/TSCALE,
  g_12 = 1.5*logtp1/TSCALE;

      double 
  y   = H[i][j]+g-Ho,
  y1  = H1[i][j]+g_1,
  y2  = H2[i][j]+g_2,
  y12 = H12[i][j]+g_12;
      Qextrapolate_u0tinf(  &y,&y1,&y2,&y12,
           u_field[i],t_field[j],
           u,t, Y, Y1, Y2 );
      (*Y)   = (*Y) - f + Ho;
      (*Y1)  -= f1;
      (*Y2)  -= f2;
      return;
    }
    else if( a == 7 ) { // u --> oo, t --> oo 
#ifndef NO_PO_INTERPOL
      if(PrintFlag) printf("u->oo, t->oo\n");
#endif
      double T = t/TSCALE;
      double                       // interpolate shifted function:
  f   = 1.5*u*T*log(T),
  f1  = 1.5*  T*log(T),
  f2  = 1.5*u*(log(T)+1.0)/TSCALE,
  
  u1 = u_field[i],
  t2 = t_field[j]/TSCALE,
  tlogt = t2*log(t2),
  logtp1 = log(t2)+1.0,
  
  g = 1.5*u1*tlogt,
  g_1 = 1.5*tlogt,
  g_2 = 1.5*u1*logtp1/TSCALE,
  g_12 = 1.5*logtp1/TSCALE;
      double 
  y   = H[i][j]+g,
  y1  = H1[i][j]+g_1,
  y2  = H2[i][j]+g_2,
  y12 = H12[i][j]+g_12;
      Qextrapolate_uinftinf(  &y,&y1,&y2,&y12,
          u_field[i],t_field[j],
          u,t, Y, Y1, Y2 );
      (*Y)   -= f;
      (*Y1)  -= f1;
      (*Y2)  -= f2;
      return;
    }
    else if( a == 8 ) { // u --> oo, t --> 0 
#ifndef NO_PO_INTERPOL
      if(PrintFlag) printf("u -> oo t -> 0\n"); 
#endif
      double 
  y   = H[i][j],
  y1  = H1[i][j],
  y2  = H2[i][j],
  y12 = H12[i][j];
      Qextrapolate_uinft0(  &y,&y1,&y2,&y12,
          u_field[i],t_field[j],
          u,t, Y, Y1, Y2 );
    }
    else if( a == 9 ) { // table corner 
      printf("\nLIB-ERROR in QIPscheme::Interpolate ---> Construction site !!!\n");
      exit(0);
    }
    else { printf("\nLIB-ERROR in QIPscheme::Interpolate ---> Out of table range at (%e %e) !!!\n",u,t); exit( 0 ); } 
  return;
}

//////////////////////////////////////////////////////////////////

void QIPscheme::Qbcucof(double* y,double* y1,double* y2,double* y12,
      double x1l,double x2l,double** c)
{  
  int l,k,j,i;
  double xx, cl[16], x[16],
  dd = x1l*x2l;
  for (i=1;i<=4;i++) {
    x[i-1]  = y[i];
    x[i+3]  = y1[i]* x1l;
    x[i+7]  = y2[i]* x2l;         // Transformation
    x[i+11] = y12[i]* dd;
  }
  for (i=0;i<=15;i++) {
    xx=0.0;
    for (k=0;k<=15;k++) xx += wtQ[i][k]*x[k];
    cl[i]=xx;
  }
  l=0;
  for (i=1;i<=4;i++)
    for (j=1;j<=4;j++) c[i][j]=cl[l++];
  return;
} 

//////////////////////////////////////////////////////////////////

void QIPscheme::Qextra_8cof(double* y,double* y1,double* y2,double* y12,
      double x1,double x2,double** c,int which )
{
  int l,k,j,i;
  double **GMatrix;
  double xx, cl[8], x[8],
    dd = x1*x2;
  switch(which) {
  case 1 : GMatrix = matextra_t0; break;
  case 2 : GMatrix = matextra_t_inf; break;
  case 3 : GMatrix = matextra_u0; break;
  case 4 : GMatrix = matextra_u_inf; break;
  default : { printf( "\nLIB-ERROR in QIPscheme::Qextra_8cof !!!\n" ); exit(0); }
  }
  for (i=1;i<=2;i++) {
    x[i-1]  = y[i];
    x[i+1]  = y1[i]* x1;
    x[i+3]  = y2[i]* x2;         // Transformation
    x[i+5]  = y12[i]* dd;
  }
  for (i=0;i<=7;i++) {
    xx=0.0;
    for (k=0;k<=7;k++) xx += GMatrix[i][k]*x[k];
    cl[i]=xx;
  }
  l=0;
  for (i=1;i<=2;i++)
    for (j=1;j<=4;j++) c[i][j]=cl[l++];
  return;
}
 
//////////////////////////////////////////////////////////////////

void QIPscheme::Qextra_4cof(double* y,double* y1,double* y2,double* y12,
      double x1,double x2,double** c,int which )
{
  int l,k,j,i;
  double **GMatrix;
  double xx, cl[4], x[4],
    dd = x1*x2;
  switch(which) {
  case 5 : GMatrix = matextra_u0t0; break;
  case 6 : GMatrix = matextra_u0tinf; break;
  case 7 : GMatrix = matextra_uinftinf; break;
  case 8 : GMatrix = matextra_uinft0; break;
  default : { printf( "\nLIB-ERROR in QIPscheme::Qextra_4cof !!!\n" ); exit(0); }
  }
  x[0]  = (*y);
  x[1]  = (*y1)* x1;
  x[2]  = (*y2)* x2;         // Transformation
  x[3]  = (*y12)* dd;
  
  for (i=0;i<=3;i++) {
    xx=0.0;
    for (k=0;k<=3;k++) xx += GMatrix[i][k]*x[k];
    cl[i]=xx;
  }
  l=0;
  for (i=1;i<=2;i++)
    for (j=1;j<=2;j++) c[i][j]=cl[l++];
  return;
} 
 
//////////////////////////////////////////////////////////////////

void QIPscheme::Qbcuint(double* y,double* y1,double* y2,double* y12,
      double x1l,double x1u,double x2l,double x2u,
      double x1,double x2,double* ansy,double* ansy1, double* ansy2)
{
  int i;
  double t,u,**c,
    tlogt,ulogu,
    logup1,logtp1;
  c = dmatrix(1,4,1,4);
  Qbcucof(y,y1,y2,y12,x1l,x2l,c);

  t = x1 / x1l;
  u = x2 / x2l;
  tlogt = t *log(t);
  ulogu = u *log(u);
  logup1 = log(u)+1.0;
  logtp1 = log(t)+1.0;
  *ansy=(*ansy2)=(*ansy1)=0.0;
  for (i=3;i>=1;i--) {
    *ansy  = t*(*ansy)+ c[i][4]*ulogu +c[i][3]*u*u+c[i][2]*u+c[i][1];
    *ansy2 = t * (*ansy2) + 2.0*c[i][3]*u + c[i][2] + logup1*c[i][4];
    *ansy1 = u * (*ansy1) + 2.0*c[3][i]*t + c[2][i] + logtp1*c[4][i];
   }
   *ansy  += tlogt* ( c[4][4]*ulogu+c[4][3]*u*u+c[4][2]*u+c[4][1]);
   *ansy1 += ulogu* ( 2.0*c[3][4]*t + c[2][4] + logtp1*c[4][4] );
   *ansy2 += tlogt* ( 2.0*c[4][3]*u + c[4][2] + logup1*c[4][4] );
  *ansy1 /= x1l;
  *ansy2 /= x2l;
  delete_dmatrix(c, 1,4,1,4);
  return;
}
 
//////////////////////////////////////////////////////////////////

double getQ( double p,double r,double T,int printflag )
{
  // get charge from pressure, all in cgs units
  
  double z1,ar,z2;
  //  cold :
  //  return (M_proton/r)*1.4734*pow(C1,ZWEI_FUENFTEL)*pow( p ,DREI_FUENFTEL )* 1.40605e16;
  //
  if( r<(2.0*ZERO) ) return 0.0;
  ar = p/ ( 2.0*C1_CGS*pow( T, 2.5 )/3.0);
  z1 = fermi_1( 3,ar ); 
  z2 = quickfermi_th( z1 );
  if (fabs(z2)<1.0e-99) {
    printf("\nLIB-ERROR in getQ ---> Argument p = %e, z1 = %e z2 = %e !!!\n",ar,z1,z2 );
    exit(0);
  }
    if( ar>1.0e12) {
#ifndef NO_PO_INTERPOL
    if(printflag) printf( " getQ: work with cold data.\n" );
#endif
    return (M_proton/r)*1.4734*pow(C1,ZWEI_FUENFTEL)*pow( p ,DREI_FUENFTEL )* 1.40605e16;
  }
  else
  return (M_proton/r)*C1_CGS*pow( T, 1.5 )*quickfermi_oh(z1); 
}

//////////////////////////////////////////////////////////////////
// eof.