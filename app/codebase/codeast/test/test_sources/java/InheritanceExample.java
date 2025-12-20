public class Animal {
    public void speak() {
        System.out.println("Animal speaks");
    }
}

public class Dog extends Animal {
    @Override
    public void speak() {
        System.out.println("Woof");
    }
}

public class Cat extends Animal {
    @Override
    public void speak() {
        System.out.println("Meow");
    }
}

