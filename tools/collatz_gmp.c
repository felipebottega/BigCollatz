#include <gmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

int main(int argc,char**argv){
 if(argc!=3){fprintf(stderr,"usage: %s input output\n",argv[0]);return 2;}
 FILE *f=fopen(argv[1],"r"); if(!f){perror("input");return 2;}
 mpz_t start,start_odd,n,temp,maximum; mpz_inits(start,start_odd,n,temp,maximum,NULL);
 if(mpz_inp_str(start,f,10)==0){fprintf(stderr,"bad integer\n");return 2;} fclose(f);
 mpz_set(n,start); mpz_set(maximum,start); mp_bitcnt_t start_v=mpz_scan1(start,0);
 mpz_tdiv_q_2exp(n,n,start_v); mpz_set(start_odd,n);
 unsigned long long steps=start_v, odd_steps=0; time_t begun=time(NULL);
 if(mpz_cmp_ui(n,1)==0) goto reached;
 for(;;){
   mpz_mul_ui(temp,n,3); mpz_add_ui(temp,temp,1); steps++; odd_steps++;
   if(mpz_cmp(temp,maximum)>0) mpz_set(maximum,temp);
   mp_bitcnt_t a=mpz_scan1(temp,0);
   mpz_tdiv_q_2exp(n,temp,a);
   if(mpz_cmp(n,start_odd)==0 && a>=start_v){
     steps += (unsigned long long)(a-start_v);
     FILE*out=fopen(argv[2],"w");
     fprintf(out,"outcome=repeated_state\nsteps=%llu\nodd_steps=%llu\nwall_seconds=%lld\nmaximum=",steps,odd_steps,(long long)(time(NULL)-begun));
     mpz_out_str(out,10,maximum); fputc('\n',out); fclose(out); break;
   }
   steps += (unsigned long long)a;
   if(mpz_cmp_ui(n,1)==0){
reached:
     FILE*out=fopen(argv[2],"w");
     fprintf(out,"outcome=reached_one\nsteps=%llu\nodd_steps=%llu\nwall_seconds=%lld\nmaximum=",steps,odd_steps,(long long)(time(NULL)-begun));
     mpz_out_str(out,10,maximum); fputc('\n',out); fclose(out); break;
   }
   if(odd_steps%1000000==0) fprintf(stderr,"odd=%llu steps=%llu elapsed=%lld\n",odd_steps,steps,(long long)(time(NULL)-begun));
 }
 mpz_clears(start,start_odd,n,temp,maximum,NULL); return 0;
}
