//////////////////////////////////////////////////////////////////
// common tools for reading ascii files (e.g. 'namelist' input) 
// used by the FEOS library, the FEOS table generation tool, and by SHOWEOS
// last change: 2013-07-01
//////////////////////////////////////////////////////////////////

#ifndef COMMON_READFILE_H
#define COMMON_READFILE_H

//////////////////////////////////////////////////////////////////
// header-files:

#include "COMMON-00_DEFINITS.H"
#include "COMMON-01_UTILITIES.H"

//////////////////////////////////////////////////////////////////
// definitions:

#define MAX_LINE_LENGTH 1000
#define MAX_LINE_NO 150
#define MAX_COL 50

//////////////////////////////////////////////////////////////////
// classes and routines in COMMON-02_READFILE.C:

// readfile-class - reads parameter file:
class readfile {
  public:
           readfile();
    void   openinput( char* );
    void   closeinput( void );
    int    setinput( char* );
    char*  getinput( char* );
    char*  setget( char*, char* );
    int    lookfor( char*, char* );
    int    read_one_line( void );
    void   write_one_line( void );
    int    file_structure( int*, int*, int* );
    int    read_line( int*, char** );
    int    read_col( double*, int, int );
    void   copy_file( char*, char* );
    int    compare_files( char*, char* );
    char** cmatrix( long, long );
    void   free_cmatrix( char** );
    char*  cvector( long );
    void   free_cvector( char* );
    int    getTableSize( int*, int* ); 
  private:
    int  already_open;
    FILE *fd;
    char *buffer;
    char *result; 
};

//////////////////////////////////////////////////////////////////

#endif

//////////////////////////////////////////////////////////////////
// eof.