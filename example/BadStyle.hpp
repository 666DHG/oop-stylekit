// 这个文件故意缺少完整 V1.3 文件注释字段。
#ifndef BAD_STYLE_HPP
#define DIFFERENT_BAD_STYLE_GUARD

#define bad_limit 100
#define BAD_ADD(A,B) ((A)+(B))

const unsigned int MaxDay = 31;
int HeaderGlobalValue;

void badHelper(int, char*);

class bad_sample {
public:
    int PublicCount;
    bool Ready;
    const int& Alias;

private:
    unsigned int m_Year;
    int Count;
    char *Name;
    bool done;
};

int HeaderFunctionDefinition(int Value) { return Value + bad_limit; }

#endif

