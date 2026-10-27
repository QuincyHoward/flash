##################################################################
## FEOS makefile                                                   
## last change: 2013-07-01                                         
##################################################################

TARGET_LIBFEOS = libfeos.a
TARGET_FEOS    = feos
TARGET_SHOWEOS = showeos

TARGETD = $/../EOS-Data
SRCPATH = .

SOURCES_LIBFEOS = COMMON-01_UTILITIES.C COMMON-02_READFILE.C LIB-01_TF_SERVICES.C LIB-02_TF_TABLE_1.C LIB-02_TF_TABLE_2.C \
                  LIB-03_TF_MIXTURE.C LIB-04_IONMOD.C LIB-05_EOS_SERVICES.C LIB-06_MAXWELL.C LIB-07_C_INTERFACE.C LIB-08_FORTRAN_INTERFACE.C
OBJECTS_LIBFEOS = COMMON-01_UTILITIES.o COMMON-02_READFILE.o LIB-01_TF_SERVICES.o LIB-02_TF_TABLE_1.o LIB-02_TF_TABLE_2.o \
                  LIB-03_TF_MIXTURE.o LIB-04_IONMOD.o LIB-05_EOS_SERVICES.o LIB-06_MAXWELL.o LIB-07_C_INTERFACE.o LIB-08_FORTRAN_INTERFACE.o
SOURCES_FEOS    = COMMON-01_UTILITIES.C COMMON-02_READFILE.C FE-01_TABTOOLS.C FE-02_CALCULATIONS.C FE-03_MAIN.C
OBJECTS_FEOS    = COMMON-01_UTILITIES.o COMMON-02_READFILE.o FE-01_TABTOOLS.o FE-02_CALCULATIONS.o FE-03_MAIN.o
SOURCES_SHOWEOS = COMMON-01_UTILITIES.C COMMON-02_READFILE.C SE-01_READTABLE.C SE-02_INTERPOLTOOLS.C SE-03_SERVICES.C SE-04_MAIN.C
OBJECTS_SHOWEOS = COMMON-01_UTILITIES.o COMMON-02_READFILE.o SE-01_READTABLE.o SE-02_INTERPOLTOOLS.o SE-03_SERVICES.o SE-04_MAIN.o

LIBS_FEOS    = -lm -lfeos
LIBS_SHOWEOS = -lm
LIBDIRS      = -L.

# For debugging use -g instead of -O3:
CFLAGS = -O3 -Wall

INCDIRS = -I$(SRCPATH)

# The standard environment variable for the C++ compiler is $(CXX):
LINK              = $(CXX)
LINKFLAGS_FEOS    = $(LIBDIRS) $(LIBS_FEOS)
LINKFLAGS_SHOWEOS = $(LIBS_SHOWEOS)

LIBRARY      = ar
LIBRARYFLAGS = -rcs

RM        = rm
RMFLAGS   = -f
DATA      = ?
EMACSBACK = *~

##################################################################

$(TARGET_LIBFEOS): $(SOURCES_LIBFEOS) $(OBJECTS_LIBFEOS)
	$(LIBRARY) $(LIBRARYFLAGS) $(TARGET_LIBFEOS) $(OBJECTS_LIBFEOS)
	@ echo $(TARGET_LIBFEOS) created

##################################################################

$(TARGET_FEOS): $(SOURCES_FEOS) $(OBJECTS_FEOS)
	$(LINK) -o $(TARGET_FEOS) $(OBJECTS_FEOS) $(LINKFLAGS_FEOS) $(CFLAGS) $(INCDIRS)
	@ -cp $(TARGET_FEOS) $(TARGETD)/;
	@ echo $(TARGET_FEOS) created and copied to $(TARGETD)/

##################################################################

$(TARGET_SHOWEOS): $(SOURCES_SHOWEOS) $(OBJECTS_SHOWEOS)
	$(LINK) -o $(TARGET_SHOWEOS) $(OBJECTS_SHOWEOS) $(LINKFLAGS_SHOWEOS) $(CFLAGS) $(INCDIRS)
	@ -cp $(TARGET_SHOWEOS) $(TARGETD)/;
	@ echo $(TARGET_SHOWEOS) created and copied to $(TARGETD)/

##################################################################

all:
	make $(TARGET_LIBFEOS)
	make $(TARGET_FEOS)
	make $(TARGET_SHOWEOS)

##################################################################

.C.o:
	$(CXX) $(CFLAGS) $(INCDIRS) -c $<

##################################################################

clean:
	$(RM) $(RMFLAGS) *.o $(TARGETD)/$(TARGET_FEOS) $(TARGETD)/$(TARGET_SHOWEOS) $(TARGET_LIBFEOS) $(TARGET_FEOS) $(TARGET_SHOWEOS) $(DATA) $(EMACSBACK)
	@ echo all object files, executables and library deleted

##################################################################
## eof.