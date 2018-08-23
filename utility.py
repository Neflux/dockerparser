class Instruction(str):
    def __new__(cls, text, original_indexes):
        return super(Instruction, cls).__new__(cls, text)

    def __init__(self, text, original_indexes):
        self.key = text.split(" ")[0]
        if not isinstance(original_indexes, list):
            original_indexes = [original_indexes]
        self.original_indexes = original_indexes

    def __repr__(self):
        return super(Instruction, self).__repr__()
    
    def __str__(self):
        return super(Instruction, self).__str__()

    def __get__(self, instance, owner):
        return super(Instruction, self).__get__()

    @property
    def index(self):
        return self.original_indexes

    """def __set__(self, instance, value):
        self.new_text = value

    def get_updated_instruction(self):
        return self.new_text"""

class Dockerfile(list):
    def __init__(self):
        pass

    def __repr__(self):
        final_repr = bcolors.BOLD+"\nline\tinstruction"+bcolors.ENDC
        for inst in self:
            final_repr += "\n"+",".join(str(x+1) for x in inst.index)+"\t"
            if inst.key == "#":
                final_repr += bcolors.OKGREEN+inst+bcolors.ENDC
            elif inst.key in ["RUN","COPY","ADD"]:
                final_repr += bcolors.HEADER+inst+bcolors.ENDC
            else:
                final_repr += inst
        return final_repr
    
    def __str__(self):
        return self.__repr__()                                                                                                         

    def __getitem__(self, key):
        if isinstance(key, int):
            return super(Dockerfile, self).__getitem__(key)
        elif isinstance(key, str):
            return [x for x in self if x.key == key]

    def replace(self, x, y):
        for idx, inst in enumerate(self):
            if inst == x:
                self[idx] = Instruction(y, inst.index)
                break
    
    def remove(self, x):
        """if isinstance(x, list):
            for inst in x:
                super(Dockerfile, self).remove(inst)
        else:
            super(Dockerfile, self).remove(x)"""
        if isinstance(x, list):
            tmp = [inst for idx, inst in enumerate(self) if inst not in x]
            self.clear()
            self.extend(tmp)
        else:  
            tmp = [inst for inst in self if inst != x]
            self.clear()
            self.extend(tmp)

    def insert(self, idx, x):
        """if isinstance(x, list):
            print("list")
            for inst in x:
                if idx in inst.index:
                    super(Dockerfile, self).insert(idx,x)
                    break
        else:"""
        super(Dockerfile, self).insert(idx, Instruction(x,idx))          

    # Number of instructions generating a layer
    @property
    def layers(self):
        return len([x for x in self if x.key in ["RUN","COPY","ADD"]])
    
    # Number of non-comment instructions
    @property
    def len(self):
        return len([x for x in self if x.key != "#"])

# Console colors
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'