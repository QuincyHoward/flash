//////////////////////////////////////////////////////////////////
// common tools for reading ascii files (e.g. 'namelist' input) 
// used by the FEOS library, the FEOS table generation tool, and by SHOWEOS
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////
// thanks to Rafael Ramis, Madrid, for some of the following functions 
//////////////////////////////////////////////////////////////////
// openinput(file)       has to be called to open/rewind the input file, 
// closeinput(file)      has to be called to close input file, 
// setinput(k)           can be used to set the file pointer to the key 'k' 
// getinput(a)           scans the file for variable name 'a' and returns the string beyond 'a=' 
// setget(k,a)           resets the file pointer to the key word 'k',
//                       scans the following lines completely for the desired member variable
//                       'a', allowing for variables seperated by commata ( NAMELIST )
//		                   returns string following 'a='
// lookfor(k,a)          resets the file pointer to the key word 'k',
//                       scans the following lines completely for the desired member variable
//                       'a', allowing for variables seperated by commata ( NAMELIST )
//                       returns value 1 if found, otherwise value 0
// read_one_line()       reads single lines of the input file skipping blanks and comments
// write_one_line()      writes the recently read line to stdout
// file_structure(c,r)   get number of columns and rows
// read_line(narg,arg)   reads columns of a single line into the argument list '**arg' 
//                       and the number of arguments into '*narg', skipping comments
//                       return value 1 for successful reading, 0 for end of file
// read_col(d,col,rows)  reads data in column 'col' into the vector 'd'
//                       maximum number of rows to read is specified by 'rows'    
// copy_file(a,b)        copies file a to file b
// compare_files(a,b)    compare file a with file b
//////////////////////////////////////////////////////////////////

#include "COMMON-02_READFILE.H"

//////////////////////////////////////////////////////////////////
  
readfile::readfile()
{
  already_open = 0;
  buffer = new char [MAX_LINE_LENGTH];
  if(!buffer){ printf( "\nCOMMON-ERROR in readfile::readfile ---> Allocation error !!!\n" ); exit(0);}
  result = new char [MAX_LINE_LENGTH];
  if(!result){ printf( "\nCOMMON-ERROR in readfile::readfile ---> Allocation error !!!\n" ); exit(0);}
}

//////////////////////////////////////////////////////////////////

int readfile::getTableSize( int* NR, int* NT )
{ 
  // corresponds to structure of TF-table

  char** arg;
  int narg,nr,nt;
  arg = cmatrix( MAX_LINE_NO , MAX_LINE_LENGTH );
  nr = nt = 0;
  while( read_line( &narg, arg ) != 0 ) { 
    if(arg[0][0]!='#'){ 
      if( narg==1 ) nr++; 
      else nt++;
    } 
  }
  if(nr==0) { printf("\nCOMMON-ERROR in readfile::getTableSize ---> No table entries found !!!\n"); exit(0); }
  nt = int( nt/nr );
  
  *NR = nr;
  *NT = nt;
  free_cmatrix(arg);
  rewind(fd);
  return 0;
}

//////////////////////////////////////////////////////////////////

void readfile::openinput(char *file)
{
  // openinput() has to be called to open the file.
  // If the file is already open, the file pointer is reset to the begining
   
  if(!already_open){
    fd=fopen(file,"r");
    if(fd==NULL){
      printf("\nCOMMON-ERROR in readfile::openinput ---> Can't open file %s !!!\n", file);
      exit(1);
    }
    already_open=1;
  }
  else {
    rewind(fd);
  }
}

//////////////////////////////////////////////////////////////////

void readfile::closeinput( void )
{
  if(already_open){
    int value=fclose( fd );
    already_open=0;
    if(value!=0){printf("\nCOMMON-ERROR in readfile::closeinput ---> File not correctly closed !!!\n");exit(0);}
  }
}

//////////////////////////////////////////////////////////////////

int readfile::setinput(char *a) 
{
  // This funtion moves the file pointer beyond the line that contains string 'a' 
  // and returns 1. Blanks and comments ("#" followed by some text) are ignored. 
  // If 'a' is not found, 0 is returned. 
  // The file has to be opened previouslly by openinput().

  int m,n;

  n = strlen(a);

  rewind(fd);

  while(read_one_line()){
    m=strlen(buffer);
    if(m==n){
      if(strncmp(buffer,a,n)==0)return(1);
    }
  }

  return(0);
}

//////////////////////////////////////////////////////////////////
 
char* readfile::setget(char *key, char *a) 
{
  // set file pointer beyond the key word 'key',
  // scan following lines for variable 'a',
  // and return string following 'a='.
  // break, if next key word (beginning with '&') is reached before 'a'

  int m,i,n,j=0;

  n = strlen(a);
                                                   // reset file pointer to the key word
  if (!setinput(key)) {
    printf( "\nCOMMON-ERROR in readfile::setget ---> Key word '%s' missing !!!\n", key );
    exit(-1);
  }   

  while(read_one_line()){                        // read lines following the key
    m=strlen(buffer);
    if (strchr(buffer,38)) break;                // '&' contained -> break
    if(m>n+1) {                                  // length sufficient
      for(i=0;i<m-n;i++) {                       // scan the line for variable name
	      if(strncmp(buffer+i,a,n)==0){            // if found, write it to result[]
	        if(buffer[n+i]=='='){
	          i++;
	          while(buffer[n+i+j]!=',' && n+i+j<m ) {
	            result[j]=buffer[n+i+j]; 
	            j++;
	          }
	          result[j]=0;
	          return(result);                        // and return pointer to result
	        }
	      }
      }
    }
  }
  printf("\nCOMMON-ERROR in readfile::setget ---> Can't find name");   // otherwise: send error message
  for(i=0;i<n;i++)putchar(a[i]);
  printf(" following key word %s !!!\n",key); 
  exit(1);
  return(result);
}

//////////////////////////////////////////////////////////////////
 
int readfile::lookfor(char *key, char *a) 
{
  // set file pointer beyond the key word 'key',
  // scan following lines for variable 'a',
  // and return value 1 if 'a' is found, otherwise value 0.
  // break, if next key word (beginning with '&') is reached before 'a'

  int m,i,n;

  n = strlen(a);
                                                   // reset file pointer to the key word
  if (!setinput(key)) {
    printf( "\nCOMMON-ERROR in readfile::lookfor ---> Key word '%s' missing !!!\n", key );
    exit(-1);
  }   

  while(read_one_line()){                        // read lines following the key
    m=strlen(buffer);
    if (strchr(buffer,38)) break;                // '&' contained -> break
    if(m>n+1) {                                  // length sufficient
      for(i=0;i<m-n;i++) {                       // scan the line for variable name
	      if(strncmp(buffer+i,a,n)==0) return(1);  // if found, return 1
      }
    }
  }
  return(0);   // otherwise: return 0
}

//////////////////////////////////////////////////////////////////

char* readfile::getinput(char *a) 
{
  // scan the file for variable name 'a' and return the string beyond 'a='
  
  int m,n,i=0,j=0;

  n = strlen(a);

  rewind(fd);

  while(read_one_line()){                        // read lines 
    m=strlen(buffer); 
    if(m>n+1) {                                  // length sufficient
      for(i=0;i<m-n;i++) {                       // scan the line for variable name
	      if(strncmp(buffer+i,a,n)==0){            // if found, write it to result[]
	        if(buffer[n+i]=='='){
	          i++;
	          while(buffer[n+i+j]!=',' && n+i+j<m ) {
	            result[j]=buffer[n+i+j]; 
	            j++;
	          }
	          result[j]=0;
	          return(result);                      // and return pointer to result
	        }
	      }
      }
    }
  }
  printf("\nCOMMON-ERROR in readfile::getinput ---> Can't find name");
  for(i=0;i<n;i++) putchar(a[i]);
  printf(" in input file !!!\n"); 
  exit(1);
  return(result);
}

//////////////////////////////////////////////////////////////////

int readfile::read_one_line( void )
{
  // read one line into buffer, skip blanks and comments (following '#')
 
  int i=0,c;
  while(i<MAX_LINE_LENGTH){
    c=getc(fd); 
    if(c==EOF)return(0);
    else if(c=='\n'){
      buffer[i++]=0; 
      return(1);
    }
    else if(c=='#'){
      buffer[i++]=0;
      while(getc(fd)!='\n');
      return(1);
    }
    else if(c!=' '){
      buffer[i++]=c;
    }
  }
  printf("\nCOMMON-ERROR in readfile::read_one_line ---> Line too long !!!\n");
  exit(-1);
  return(-1);
}

//////////////////////////////////////////////////////////////////

void readfile::write_one_line( void )
{
  int i=0;
  
  printf( "\n" );
  while( buffer[i]!=0 ) putchar(buffer[i++]); 
}

//////////////////////////////////////////////////////////////////

int readfile::file_structure( int *col_min, int *col_max, int *rows )
{
  // read file, count number of rows and find minimum and maximum number of columns 
  
  int check, narg;
  char **arg;

  rewind(fd);

  arg = cmatrix(MAX_COL,MAX_LINE_LENGTH);
  if(!arg){ printf( "\nCOMMON-ERROR in readfile::file_structure ---> Allocation error !!!\n" ); exit(0);}

  *col_min = MAX_COL;
  *col_max = 0;
  *rows    = 0;

  do 
    { 
      check = read_line( &narg, arg );
      if (check>0) {
	      (*rows)++;
	      if (narg<*col_min) *col_min=narg;
	      if (narg>*col_max) *col_max=narg;
      }
    }
  while( check>0 );

  free_cmatrix(arg);

  if ((*col_min)==(*col_max)) return 1;
  else                        return 0;
}

//////////////////////////////////////////////////////////////////

int readfile::read_col( double *data, int col, int rows_max )
{
  // read data from column 'col' into 'data', maximum number of rows ('rows_max')
  
  int rows_count=0;
  int narg, nmin=MAX_COL, nmax=0;
  char **arg;
  int check;

  if (col==0) { printf( "\nCOMMON-ERROR in readfile::read_col ---> Selected colum number %d invalid !!!\n", col ); exit(-1); }

  arg = cmatrix(MAX_COL,MAX_LINE_LENGTH);
  if(!arg){ printf( "\nCOMMON-ERROR in readfile::read_col ---> Allocation error !!!\n" ); exit(0);}

  rewind(fd);

  do 
    { 
      check = read_line( &narg, arg );
      if (narg>=col) data[rows_count++] = atof( arg[col-1] );
      else 
	    { 
	      data[rows_count++] = 0;
	      printf( "\nWARNING from readfile::read_col ---> %d column(s) in line %d !\n", narg, rows_count );
	    }
      if (narg<nmin) nmin=narg;
      if (narg>nmax) nmax=narg;
    }
  while( check>0 && rows_count<rows_max );

  //  if (nmin==nmax) printf( "\n %d rows, %d cols", rows_count, nmax );
  //  else            printf( "\n %d rows, %d...%d cols", rows_count, nmin, nmax );

  free_cmatrix(arg);

  return rows_count;
}

//////////////////////////////////////////////////////////////////

int readfile::read_line( int *narg, char **arg )
{
  // read several arguments from one line 
  // arguments have to be se seperated by blanks
  // a line is terminated with '\n'
  // lines of blanks are skipped
  // comments are skipped ( anything following a '#' )
  //
  // narg: number of arguments that have been read
  // arg[]: pointer to strings containing the arguments
  //
  // return value: 0, if end of file was reached
  //               1, if arguments were read successfully 
  
  int c, col=0, pos=0, skip=0;

  do 
  {
    c=getc(fd); 
    arg[col][pos]=0; 
    if ( c=='#' )       
	  { 
	    if (pos>0) col++;
	    pos=0;
	    skip++; 
	  }
    else if ( c==' ' )  
	  { 
	    if (pos>0) col++;
	    pos=0;
	  }
    else if ( c=='\n' ) 
	  { 
	    if (pos>0) col++;
	    pos=0;
	    *narg=col;
	    if (col>0) return 1;
	    else       skip=0; 
	  }
    else if ( c==EOF )  
	  { 
	    if (pos>0) col++;
	    *narg=col;
	    return 0; 
	  }
    else if ( skip==0 ) arg[col][pos++] = c; 
  }
  while( col<MAX_COL && pos<MAX_LINE_LENGTH);
  
  if (col>=MAX_COL) printf( "\nCOMMON-ERROR in readfile::read_line ---> Number of columns too large !!!\n" ); 
  else              printf( "\nCOMMON-ERROR in readfile::read_line ---> Length of argument too large !!!\n" ); 
  exit(-1);
  return(-1);  
}

////////////////////////////////////////////////////////////////// 

void readfile::copy_file( char *input, char *output )
{
  // copy file 'input' to file 'output'
  
  FILE *fin, *fout;
  int c, diff;
  char backup[MAX_LINE_LENGTH];

  diff=compare_files(input,output); 

  if (diff>0) {      // files exist and differ
    printf( "readfile::copy_file: File %s does exist \n", output );
    printf( "                     and is different from %s\n", input );
    sprintf( backup, "%s-backup", output );
    copy_file( output, backup );
    printf( "                     %s saved to %s\n", output, backup );
  }

  if (diff==0) {     // files are identical
      printf( "readfile::copy_file: File %s does exist \n", output );
      printf( "                     and is equal to %s -> not copied\n", input );
  }
  else {             // one file does not exist so far
    fin = fopen( input, "rb" );
    fout = fopen( output, "wb" );
    while( (c=fgetc(fin)) != EOF ) fputc(c,fout);
    fclose( fin );
    fclose( fout );
  }
}

//////////////////////////////////////////////////////////////////

int readfile::compare_files( char *name1, char *name2 )
{
  // if one or two of these files do not exist: return -1 
  // else:  return number of different pairs of characters

  FILE *f1, *f2;
  int c1, c2;
  int differences=0;

  f1 = fopen( name1, "rb" );
  f2 = fopen( name2, "rb" );

  if ( (!f1) || (!f2) ) return -1; 
  else {
    do {
      c1=fgetc(f1);
      c2=fgetc(f2);
      if (c1!=c2) differences++;
    } while( (c1 != EOF) && (c2 != EOF) ); 
    
    fclose( f1 );
    fclose( f2 );
    
    return differences;
  }
}

//////////////////////////////////////////////////////////////////

char** readfile::cmatrix(long nrh, long nch)
{
  // allocate a char matrix with subscript range m[0..nrh][0..nch]
  
  long i, nrow=nrh+1, ncol=nch+1;
  char **m;

  // allocate pointers to rows
  m=(char **) malloc((size_t)(nrow*sizeof(char*)));
  if (!m) printf("\nCOMMON-ERROR in readfile::cmatrix ---> Allocation failure 1 !!!\n");
  
  // allocate rows and set pointers to them
  m[0]=(char *) malloc((size_t)((nrow*ncol)*sizeof(char)));
  if (!m[0]) printf("\nCOMMON-ERROR in readfile::cmatrix ---> Allocation failure 2 !!!\n");

  for(i=1;i<=nrh;i++) m[i]=m[i-1]+ncol;

  // return pointer to array of pointers to rows
  return m;
}

//////////////////////////////////////////////////////////////////

void readfile::free_cmatrix( char **m )
{
  // free a char matrix allocated by cmatrix()
  
  free((FREE_ARG) (m[0]));
  free((FREE_ARG) (m));
}

//////////////////////////////////////////////////////////////////

char* readfile::cvector(long nch)
{
  // allocate a char vector with subscript range m[0..nch]
  
  long ncol=nch+1;
  char *m;

  // allocate pointers to columns
  m=(char*) malloc((size_t)(ncol*sizeof(char)));
  if (!m) printf("\nCOMMON-ERROR in readfile::cvector ---> Allocation failure !!!\n");
  
  // return pointer to array of pointers to rows
  return m;
}

//////////////////////////////////////////////////////////////////

void readfile::free_cvector( char *m )
{
  // free a char vector allocated by cvector()
  free((FREE_ARG) m);
}

//////////////////////////////////////////////////////////////////
// eof.