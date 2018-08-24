class Instruction(str):
    def __new__(cls, text, index):
        return super(Instruction, cls).__new__(cls, text)

    def __init__(self, text, index):
        self.key = text.split(" ")[0]
        self.index = index

    """def __repr__(self):
        return super(Instruction, self).__repr__()
    
    def __str__(self):
        return super(Instruction, self).__str__()

    def __get__(self, instance, owner):
        return super(Instruction, self).__get__()"""

class Dockerfile(list):
    def __init__(self):
        pass

    """    def append(self, instruction):
        instruction.index = len(self)
        super(Dockerfile,self).append(instruction)"""

    def __repr__(self):
        final_repr = bcolors.BOLD+"\nIndex\tInstruction"+bcolors.ENDC
        for idx, inst in enumerate(self):
            final_repr += "\n"+str(inst.index)+"\t"
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
    
    def get_index(self, a, default_index=1):
        return next((idx for idx, inst in enumerate(self) if inst == a), default_index)

    def shift(self, pos, shift):
        for idx, inst in enumerate(self):
            if idx > pos:
                inst.index += shift

    # Replace Instruction x with string y
    def replace(self,x,y):
        index = self.get_index(x)
        self[index] = Instruction(y,index)
    
    # Remove Instruction x
    def remove(self, x):
        if isinstance(x, Instruction):
            self.shift(x.index,-1)
            super().remove(x)
        elif isinstance(x, str):
            index = self.get_index(x)
            try:
                super().remove(Instruction(x,index))
                self.shift(index,-1)
            except Exception as ex:
                print("not found")

    # Insert Instruction x
    def insert(self, idx, x):
        if idx > len(self):
            idx = len(self)
        super().insert(idx,Instruction(x,idx))
        self.shift(idx,1)

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