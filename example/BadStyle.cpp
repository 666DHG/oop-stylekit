// 这个文件故意缺少完整 V1.3 文件注释字段。
#include "BadStyle.hpp"
#include "Other.cpp"

#define scale 2
#define SQUARE(X) ((X)*(X))

const int BadSize = 10;
int globalNumber;
float globalRatio;
int* globalPointer;
int values[4];

void badHelper(int value,char* text) {
	int x,y;
    int  z = 0;    
    char * pointer;
    bad_sample* object = nullptr;
    bool ready = false;
    if(value==0) x++;
    else y--;
    for(int i=0;i<3;i++) z+=i;
    while(ready) ;
    do z++; while(z<3);
    globalNumber = globalNumber + value;
    x = values[x++];
    badHelper(++value,text);
    if(globalRatio == 0.0) {
        goto End;
    }
    switch(value) {
    case 1: z++;
    case 2:
        z--;
        break;
    }
    pointer = new char[BadSize];
    delete pointer;
    object -> PublicCount = 0;
    z = value>0?value:bad_limit;
    z = BAD_ADD(value,scale); x = z;
End:
    return;
}

class DateInsideCpp {
public:
    unsigned int Year;
};

int AnotherFunction(int A) {
    return A;
}
