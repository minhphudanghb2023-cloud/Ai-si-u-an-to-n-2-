n=int(input("nhập số cho tôi "))
for i in range(n) :
    for m in range (n):
        if i==0 and m in( 1,2,3,4) or i==1 and m in(0,3,6) or i==2 and m in(1,6) or i==3 and m in( 2,5 ) or i==4 and m in(3,4)or  i==5 and m == 4:
            print(" thảo ",end=" ")
        else :
            print("  ",end=" ")
    print()