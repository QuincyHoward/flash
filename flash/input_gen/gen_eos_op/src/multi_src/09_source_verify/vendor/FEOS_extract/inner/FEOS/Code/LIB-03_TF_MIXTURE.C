//////////////////////////////////////////////////////////////////
// routines for calculation of the Thomas-Fermi EOS of a mixture 
// used by the FEOS library
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////
 
#include "LIB-03_TF_MIXTURE.H"
 
//////////////////////////////////////////////////////////////////

void mixture_getTFquantities (QIPscheme **qip, Ionpart *ip, double rho, double t, 
		   double *Pe, double *Ee, double *Se, double *Fe, double *Q, double *Qtot)
{
  // compute all thermodynamical values for electron component

  int anz = ip->Nelements;

  // check if rho and t exceed limits in DEFINITS.H (rho,t -> 0)
  if(rho <= RHO_ZERO) rho = RHO_ZERO;
  if(t <= T_ZERO) t = T_ZERO;
    
  // check if number of elements greater 1
  if(anz>1) {
	  // get all quantities for the mixture in mixture_getallquantities
	  mixture_getallquantities( qip, ip, rho, t, Pe, Ee, Se, Fe, Q, Qtot);
  }
  // else get data for single element
  else { 
    qip[0]->getTFquantities( rho, t, Pe, Ee, Se, Fe, Qtot);
    Q[0] = *Qtot;
  }

  return;
}

//////////////////////////////////////////////////////////////////

void mixture_getallquantities(QIPscheme **qip, Ionpart *ip, double rho, double t, 
		   double *Pe, double *Ee, double *Se, double *Fe, double *Q, double *Qtot)
{
  // compute all quantities for electron component of the mixture

  int i, anz, m;
  double pmean, Amean, rhotot, rhotottemp, frac, Ptemp, Etemp, Stemp, Ftemp, Qtemp;
  double *p, *r, *rtemp, *A, *X, *Xtot;
  bool endlloop;

  Amean = ip->Amean;
  anz = ip->Nelements;
  A = ip->Aelement;
  X = ip->Xelement_frac;
  Xtot = ip->Xelement_tot;
  endlloop = false;
  rhotottemp = 0.0;

  // allocate memory for pressure and density values
  p = dvector(0,anz-1);
  r = dvector(0,anz-1);
  rtemp = dvector(0,anz-1);

  // initial guess for element densities
  for(i = 0; i<anz; i++) r[i] = rho;

  // use rule for mixing of elements
  for(m = 1; m<=MAXIT; m++)
  {
	  // compute mean value of all pressures  	
	  pmean = 0.0;
	  for(i = 0; i<anz; i++)
  	{
		  p[i] = qip[i]->getquantity( r[i], t, 1 );
      pmean += p[i] * X[i];
  	}

	  // compute r[i] such that p[i] = pmean
	  // compute rhotot at pmean by the additive volume rule
	  rhotot = 0.0;
	  for(i = 0; i<anz; i++)
	  {
		  getrho_Ridder( qip[i], r+i, pmean, t );
	    rhotot += X[i]*A[i]/r[i];
    }
	  rhotot = Amean/rhotot;

	  // if rhotot equal to rho: finish
	  if (fabs(rhotot-rho) <= RHO_PREC * rho) break;
	  // else rescale r[i] such that rhotot = rho and check for possible endless loop
	  else
	  {
		  // check for possible endless loop
		  if(m%2 && endlloop==false)
		  {
		    if(m>2 && fabs(rhotot-rhotottemp) <= RHO_PREC * rho) endlloop = true;
		    rhotottemp = rhotot;
		  }
		  // rescale r[i] such that rhotot = rho and eliminate possible endless loop
		  frac = rho / rhotot;
		  for(i = 0; i<anz; i++) 
		  {
		    r[i] = frac * r[i];
			  if(endlloop==true) r[i] = (r[i] + rtemp[i]) / 2;
			  rtemp[i] = r[i];
		  }
	  }
  }

  // check if number of iterations under the limit
  if(m==MAXIT+1) 
  {
	printf("\nLIB-ERROR in mixture_getallquantities ---> Maximum number of iterations for computing mixture exceeded !!!\n");
	exit(1);
  }

  // get all thermodynamical values
  *Pe = pmean;
  *Ee = *Se = *Fe = *Qtot = 0.0;  
  for(i = 0; i<anz; i++)
  {
	  qip[i]->getTFquantities( r[i], t, &Ptemp, &Etemp, &Stemp, &Ftemp, &Qtemp);
	  *Ee += Etemp * X[i] * A[i] / Amean;
	  *Se += Stemp * X[i] * A[i] / Amean;
	  *Fe += Ftemp * X[i] * A[i] / Amean;
	  *Qtot += Qtemp * Xtot[i];
    Q[i] = Qtemp;
  }
  
  // free memory
  free_dvector(p, 0, anz-1);
  free_dvector(r, 0, anz-1);
  free_dvector(rtemp, 0, anz-1);

  return;
}

//////////////////////////////////////////////////////////////////

void mixture_getdpdr_solid(QIPscheme **qip, Ionpart *ip, 
		double* Pe, double* Ee, double* dpedr, double* Pe0, double* Ee0)
{
  // compute pressure, energy and dp/dr for electron component in the mixture
  // at solid-density rhosolid and standard-temperature T_standard
 
  double rho, t, dr, p1, p2, e, f, s, qtot, *q;
  q = new double[(*ip).Nelements];

  if((*ip).PrintFlag) printf("\n Compute dPe/dRho at reference temperature and density:\n");

  rho = ip->rhosolid;
  t = ip->T_standard;
  dr = EPS_DPDR*rho;

  mixture_getTFquantities(qip, ip, rho-dr, t, &p1, &e, &s, &f, q, &qtot);  
  mixture_getTFquantities(qip, ip, rho, t, Pe, Ee, &s, &f, q, &qtot); 
  mixture_getTFquantities(qip, ip, rho+dr, t, &p2, &e, &s, &f, q, &qtot); 
  *dpedr =  (p2-p1) / ( 2.0 * dr );
  mixture_getTFquantities(qip, ip, rho, 0, Pe0, Ee0, &s, &f, q, &qtot); 

  if((*ip).PrintFlag) printf("  Pe(%e g/cm^3, %e eV) = %e dyne/cm^2\n",rho,t, *Pe);
  if((*ip).PrintFlag) printf("  dPe/dRho(%e g/cm^3, %e eV) = %e dyne*cm/g\n", rho,t, *dpedr);
  if((*ip).PrintFlag) printf(" Done.\n");
  
  delete q;
  return;
}

//////////////////////////////////////////////////////////////////

int getbracketvalues(QIPscheme *qipp_i, double rho, double p, double t,
		       double *rleft, double *rright)
{
  // routine for finding bracket-rho-values around R with p(R)=p
  // for use in root finding routines (for finding R)

  int j=0;
  double pl, ph, rl, rh, minrho, bracketdelta;

  rh = rl = rho;
  ph = pl = qipp_i->getquantity( rho, t, 1 );
  bracketdelta = RHO_ZERO + BRACKET_PREC * rho;
  minrho = BRACKET_MINRHO * RHO_ZERO;

  // get bracket values rl and rh
  if(pl<p)
  {
	for(j=1; j<=MAXIT; j++)
	{
		rl = rh;
		rh += bracketdelta;
		ph = qipp_i->getquantity( rh, t, 1 );
		if(ph>=p) break;
	}
  }
  else
  {
	for(j=1; j<=MAXIT; j++)
	{
		rh = rl;
		rl -= bracketdelta;
		if(rl<minrho) rl=minrho;
		pl = qipp_i->getquantity( rl, t, 1 );
		if(pl<=p) break;
		else if(pl>=p && rl==minrho) return 0;
	}
  }

  if(j==MAXIT+1) 
  {
	printf("\nLIB-ERROR in getbracketvalues ---> Maximum number of iterations for finding bracket values exceeded !!!\n");
	exit(1);
  }

  pl = qipp_i->getquantity( rl, t, 1 ); 
  ph = qipp_i->getquantity( rh, t, 1 );

  *rleft = rl;
  *rright = rh;

  return 1;
}

//////////////////////////////////////////////////////////////////

void getrho_Ridder (QIPscheme *qip_i, double* rho, double p, double t)
{
  // routine for finding rho[i] of material i such that p[i] = p
  // Ridder's method for root finding ist used

  int k=0;
  double res, ph, pl, pm, pnew, s, rh, rl, rm, rnew;

  // find bracket values
  if(!getbracketvalues(qip_i, *rho, p, t, &rl, &rh)) return;

  // use Ridder's root finding method (from Numerical Recipes)
  pl = qip_i->getquantity( rl, t, 1 ) - p; 
  ph = qip_i->getquantity( rh, t, 1 ) - p;

  if ((pl > 0.0 && ph < 0.0) || (pl < 0.0 && ph > 0.0))
  {
	res = UNUSED;
	for (k=1; k<=MAXIT; k++)
	{
		rm = 0.5*(rl+rh);
		pm = qip_i->getquantity( rm, t, 1 ) - p;
		s = sqrt(pm*pm-pl*ph);
		if ( s == 0.0) break;
		rnew = rm + (rm - rl) * ((pl >= ph ? 1.0 : -1.0) * pm/s);
		if (fabs(rnew-res) <= RHO_PREC * (*rho)) break;
		res = rnew;
		pnew = qip_i->getquantity( res, t, 1 ) - p;
		if (pnew == 0.0) break;
		if (SIGN(pm,pnew) != pm)
		{
			rl=rm;
			pl=pm;
			rh=res;
			ph=pnew;
		}
		else if (SIGN(pl,pnew) != pl)
		{
			rh=res;
			ph=pnew;
		}
		else if (SIGN(ph,pnew) != ph)
		{
			rl=res;
			pl=pnew;
		}
		else 
		{
			printf("\nLIB-ERROR in getrho_Ridder ---> Never get here !!!\n");
			exit(1);
		}
		if (fabs(rh-rl) <= RHO_PREC * (*rho)) break;
	}
	if(k==MAXIT+1) 
  	{
		printf("\nLIB-ERROR in getrho_Ridder ---> Maximum number of iterations for finding Rho exceeded !!!\n");
		exit(1);
  	}
  }
  else
  {
	if (pl == 0.0) res = rl;
	else if (ph == 0.0) res = rh;
	else 
	{
		printf("\nLIB-ERROR in getrho_Ridder ---> Root must be bracketed !!!\n");
		exit(1);
	}
  } 

  *rho = res;

  return;
}

//////////////////////////////////////////////////////////////////
// eof.