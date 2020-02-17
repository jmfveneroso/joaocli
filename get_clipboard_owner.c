// gcc clipboard-owner.c -lX11 -o clipboard-owner

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <X11/Xlib.h>
#include <X11/Xatom.h>

#define MAX_PROPERTY_VALUE_LEN 4096

typedef unsigned long ulong;

static char *get_property(Display *, Window, Atom , const char *, ulong *);

int main(void) {
  // Open the Display
  Display *display = XOpenDisplay(NULL);

  // Get the selection window
  Window selection_owner = XGetSelectionOwner(display, XA_PRIMARY);

  if(!selection_owner) {
    exit(0);
  } else {
      char *window_name = get_property(display, selection_owner, XA_STRING, "WM_NAME", NULL);
      printf("%s\n", window_name);
  }

  XCloseDisplay(display);
}

static char *get_property (Display *disp, Window win,
        Atom xa_prop_type, const char *prop_name, ulong *size) {
    Atom xa_prop_name;
    Atom xa_ret_type;
    int ret_format;
    ulong ret_nitems;
    ulong ret_bytes_after;
    ulong tmp_size;
    unsigned char *ret_prop;
    char *ret;

    xa_prop_name = XInternAtom(disp, prop_name, False);

    if (XGetWindowProperty(disp, win, xa_prop_name, 0,
            MAX_PROPERTY_VALUE_LEN / 4, False,
            xa_prop_type, &xa_ret_type, &ret_format,
            &ret_nitems, &ret_bytes_after, &ret_prop) != Success) {
        printf("Cannot get %s property.\n", prop_name);
        return NULL;
    }

    if (xa_ret_type != xa_prop_type) {
        printf("Invalid type of %s property.\n", prop_name);
        XFree(ret_prop);
        return NULL;
    }

    /* null terminate the result to make string handling easier */
    tmp_size = (ret_format / 8) * ret_nitems;
    /* Correct 64 Architecture implementation of 32 bit data */
    if(ret_format==32) tmp_size *= sizeof(long)/4;
    ret = (char *)malloc(tmp_size + 1);
    memcpy(ret, ret_prop, tmp_size);
    ret[tmp_size] = '\0';

    if (size) {
        *size = tmp_size;
    }

    XFree(ret_prop);
    return ret;
}
